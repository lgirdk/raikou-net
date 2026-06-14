# docker-bake.hcl — raikou-net image matrix.
#
# Three variables, all overridable from the environment or `--set`:
#   VERSION   — image tag (default: read by Makefile from the VERSION file)
#   REGISTRY  — GHCR base (default: ghcr.io/ketantewari/raikou)
#   LATEST    — "yes" to also tag images with :latest; "no" to skip
#
# Groups:
#   default     — everything (orchestrator + components)
#   components  — every component image (12 targets)
#   push-set    — the 10 images published to GHCR (ssh is a build-only dep)
#
# ssh dependency: each ssh-dependent target declares
#   contexts = { "ssh:v2.0.0" = "target:ssh" }
# so bake builds ssh first and rewrites the downstream FROM at build time.

variable "VERSION"  { default = "v3" }
variable "REGISTRY" { default = "ghcr.io/ketantewari/raikou" }
variable "LATEST"   { default = "yes" }

function "ghcr_tags" {
  params = [name]
  result = LATEST == "yes" ? ["${REGISTRY}/${name}:${VERSION}", "${REGISTRY}/${name}:latest"] : ["${REGISTRY}/${name}:${VERSION}"]
}

# Single-platform on purpose: arm64 builds are out of scope for now. When/if
# we cross-compile, add "linux/arm64" here and the per-target tags pick it up.
target "_base" {
  platforms = ["linux/amd64"]
}

# ---- Orchestrator ----
target "orchestrator" {
  inherits = ["_base"]
  context  = "."
  tags     = ghcr_tags("orchestrator")
}

# ---- ssh (base for 6 downstream images) ----
# Tagged locally as ssh:v2.0.0 so downstream FROM directives still resolve
# if someone runs `docker build` outside bake.
target "ssh" {
  inherits = ["_base"]
  context  = "components/ssh"
  tags     = concat(["ssh:v2.0.0"], ghcr_tags("ssh"))
}

# ---- ssh-dependent components (push set) ----
target "router" {
  inherits = ["_base"]
  context  = "components/router"
  contexts = { "ssh:v2.0.0" = "target:ssh" }
  tags     = ghcr_tags("router")
}

target "wan" {
  inherits = ["_base"]
  context  = "components/wan"
  contexts = { "ssh:v2.0.0" = "target:ssh" }
  tags     = ghcr_tags("wan")
}

target "lan" {
  inherits = ["_base"]
  context  = "components/lan"
  contexts = { "ssh:v2.0.0" = "target:ssh" }
  tags     = ghcr_tags("lan")
}

target "dhcp" {
  inherits = ["_base"]
  context  = "components/dhcp"
  contexts = { "ssh:v2.0.0" = "target:ssh" }
  tags     = ghcr_tags("dhcp")
}

target "ntp" {
  inherits = ["_base"]
  context  = "components/ntp"
  contexts = { "ssh:v2.0.0" = "target:ssh" }
  tags     = ghcr_tags("ntp")
}

# ---- Other push-set components (no ssh dep) ----
target "cpe" {
  inherits = ["_base"]
  context  = "components/cpe/prplos"
  tags     = ghcr_tags("cpe")
}

target "acs" {
  inherits = ["_base"]
  context  = "components/acs"
  tags     = ghcr_tags("acs")
}

target "sipcenter" {
  inherits = ["_base"]
  context  = "components/sip"
  tags     = ghcr_tags("sipcenter")
}

target "sipphone" {
  inherits = ["_base"]
  context  = "components/phone"
  tags     = ghcr_tags("sipphone")
}

target "gui" {
  inherits = ["_base"]
  context  = "components/gui"
  tags     = ghcr_tags("gui")
}

# ---- Build-only (no GHCR push) ----
target "router-ethernet" {
  inherits = ["_base"]
  context  = "components/router/ethernet"
  contexts = { "ssh:v2.0.0" = "target:ssh" }
  tags     = ["router-ethernet:${VERSION}"]
}

# ---- Groups ----
group "default" {
  targets = ["orchestrator", "components"]
}

group "components" {
  targets = [
    "ssh",
    "router", "wan", "lan", "dhcp", "ntp",
    "cpe", "acs", "sipcenter", "sipphone",
    "gui",
    "router-ethernet",
  ]
}

group "push-set" {
  # ssh is intentionally excluded — it is built as a dependency (target:ssh)
  # and baked into each component, so it never needs publishing on its own.
  targets = [
    "orchestrator",
    "router", "wan", "lan", "dhcp", "ntp",
    "cpe", "acs", "sipcenter", "sipphone",
    "gui",
  ]
}
