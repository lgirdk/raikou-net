# Makefile — raikou-net build / lint / smoke / push entry point.
#
# Build matrix lives in docker-bake.hcl. This Makefile is a thin wrapper:
# build/push delegate to `docker buildx bake`; smoke wraps Vagrant; lint
# wraps pre-commit; bump rewrites the VERSION file and example .env files.
#
# Usage: `make help`.

.DEFAULT_GOAL := help
SHELL         := /bin/bash
# pipefail so a mid-stream failure in `docker save | gzip | vagrant ssh` (or
# any other recipe pipeline) actually fails the recipe instead of silently
# producing a truncated stream that downstream tools accept as "success".
.SHELLFLAGS   := -o pipefail -c

# ----- Configuration (override on CLI: `make push VERSION=v4`) -----
# REGISTRY is the image-name prefix for build/push. GHCR_REGISTRY is a legacy
# alias kept for back-compat (older invocations passed GHCR_REGISTRY=...).
# Override either: `make push REGISTRY=localhost:5000/raikou`.
GHCR_REGISTRY ?= ghcr.io/ketantewari/raikou
REGISTRY      ?= $(GHCR_REGISTRY)
VERSION       ?= $(shell cat VERSION 2>/dev/null || echo v3)
LATEST        ?= yes
DOCKER        ?= docker
COMPOSE_FILE  ?= docker-compose.ghcr.yaml
# Which examples/<dir> the lifecycle targets (demo/up/down/logs) operate on.
# `smoke` is intentionally pinned to prplos (the only example with a probe);
# see the guard below.
EXAMPLE       ?= prplos

# These names are picked up by docker-bake.hcl's `variable` blocks.
export VERSION
export LATEST
export REGISTRY

# Image targets — names match bake target names verbatim. The push-set
# (images that get GHCR tags) is declared inside docker-bake.hcl as the
# `push-set` group; this Makefile delegates to bake for `make push` and
# doesn't need to duplicate the membership list.
IMAGES := orchestrator ssh router wan lan dhcp ntp cpe acs sipcenter sipphone router-ethernet

.PHONY: help lint build build-orchestrator build-components $(IMAGES) bump push clean smoke smoke-up smoke-down smoke-logs _smoke_guard _smoke_ship _smoke_compose_up _smoke_probe demo demo-down all

# ----- Help -----
help: ## Show this help and exit
	@grep -E '^[a-zA-Z][a-zA-Z0-9_-]*:.*?## ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ----- Lint -----
lint: ## Run pre-commit on all files
	pre-commit run --all-files

# ----- Build (delegates to bake) -----
build: ## Build all images (orchestrator + components)
	$(DOCKER) buildx bake default

build-orchestrator: ## Build the orchestrator image only
	$(DOCKER) buildx bake orchestrator

build-components: ## Build all component images (no orchestrator)
	$(DOCKER) buildx bake components

$(IMAGES): ## Build a single image (e.g. `make router`)
	$(DOCKER) buildx bake $@

# ----- Bump (rewrites VERSION file + matching .env) -----
bump: ## Update VERSION file + all examples/*/.env (requires VERSION=...)
	@if [ -z "$(VERSION)" ]; then \
	  echo "ERROR: VERSION is empty"; exit 1; \
	fi
	@if ! printf '%s' '$(VERSION)' | grep -Eq '^v[0-9]+([.-][A-Za-z0-9]+)*$$'; then \
	  echo "ERROR: VERSION '$(VERSION)' must match ^v[0-9]+([.-][A-Za-z0-9]+)*$$"; exit 1; \
	fi
	@echo "$(VERSION)" > VERSION
	@found=0; \
	for envfile in examples/*/.env; do \
	  [ -f "$$envfile" ] || continue; \
	  if grep -q '^VERSION=' "$$envfile"; then \
	    sed -i.bak -E 's|^VERSION=.*|VERSION=$(VERSION)|' "$$envfile"; \
	    rm -f "$$envfile.bak"; \
	    echo "updated $$envfile"; \
	    found=$$((found+1)); \
	  fi; \
	done; \
	if [ $$found -eq 0 ]; then \
	  echo "WARNING: no examples/*/.env contained a VERSION= line; only the root VERSION was updated"; \
	fi
	@echo "VERSION → $(VERSION); review with: git diff"

# ----- Push (delegates to bake, LATEST gated by env var consumed in bake.hcl) -----
push: build ## Push the 11-image push-set to GHCR (LATEST=no to skip :latest)
	$(DOCKER) buildx bake --push push-set

# ----- Clean (remove local tags this Makefile produced) -----
clean: ## Remove local image tags this Makefile produced (no -f)
	@for img in $(IMAGES); do \
	  case "$$img" in \
	    router-ethernet) \
	      $(DOCKER) rmi "$$img:$(VERSION)" 2>/dev/null || true; \
	      continue ;; \
	    ssh) \
	      $(DOCKER) rmi "ssh:v2.0.0" 2>/dev/null || true ;; \
	  esac; \
	  $(DOCKER) rmi "$(REGISTRY)/$$img:$(VERSION)" 2>/dev/null || true; \
	  $(DOCKER) rmi "$(REGISTRY)/$$img:latest"    2>/dev/null || true; \
	done

# ----- Smoke (host ↔ Vagrant ↔ probe) -----
#
# Smoke must run inside the Vagrant VM: the CPE image exec /sbin/init,
# which interferes with host PID 1 / cgroups when run directly on the
# Docker host. The VM provides the isolation.
#
# Flow:
#   1. make build    — host builds the matrix, producing GHCR-tagged images.
#   2. vagrant up    — bring the VM up. First boot runs the provisioner
#                       (installs Docker + OVS in the VM); subsequent ups
#                       are no-ops, so this is safe to call every time.
#   3. vagrant rsync — push latest scripts/, configs, compose files.
#   4. docker save | gzip | ssh ... docker load — stream the 9 compose-
#      referenced images into the VM's docker daemon (avoids rsync'ing a
#      5+ GB tarball through the synced folder).
#   5. compose up    — start the stack with --pull=missing so the locally
#                       loaded raikou images are reused (no re-pull from
#                       GHCR), while still pulling mongo:8.0 from Docker
#                       Hub since it isn't in SMOKE_IMAGES.
#   6. smoke-probe.sh — run the four probes inside the VM.
#   7. teardown — `make smoke-down` always runs, on success and failure.
#
# Override COMPOSE_FILE=… to smoke a different compose variant later.

SMOKE_IMAGES := orchestrator router wan lan dhcp cpe acs sipcenter sipphone
SMOKE_DIR    := examples/prplos

# smoke is prplos-only: the probe (scripts/smoke-probe.sh) reads the prplos
# topology. Fail fast if pointed elsewhere rather than silently probing prplos.
ifneq ($(EXAMPLE),prplos)
_SMOKE_GUARD = @echo "ERROR: 'make smoke' only supports EXAMPLE=prplos (got '$(EXAMPLE)')." >&2; \
  echo "For the RDK LXD bench use: make demo EXAMPLE=rdk_lxd" >&2; exit 1
else
_SMOKE_GUARD = :
endif

_smoke_guard:
	@$(_SMOKE_GUARD)

smoke: _smoke_guard build ## Full smoke (prplos only): build + ship + compose up + probe + teardown
	@rm -f smoke-probe.log
	@trap '{ echo "===== SMOKE PROBE RESULT ====="; \
	         cat smoke-probe.log 2>/dev/null || echo "(probe did not run)"; \
	         echo; $(MAKE) smoke-logs; } > smoke.log 2>&1 || true; \
	       $(MAKE) smoke-down' EXIT; \
	$(MAKE) _smoke_ship && \
	$(MAKE) _smoke_compose_up && \
	$(MAKE) _smoke_probe

smoke-up: _smoke_guard build ## Build + ship + compose up (prplos only); leaves VM up for poking
	$(MAKE) _smoke_ship
	$(MAKE) _smoke_compose_up
	@echo "VM is up. Probe with: make _smoke_probe   Teardown with: make smoke-down"

# ----- Demo (no local build; runs the published GHCR stack in Vagrant) -----
# Unlike `smoke`, the demo target does not build images locally — it just
# brings the Vagrant VM up and lets the systemd unit `compose up` pull the
# published `ghcr.io/ketantewari/raikou/*:${VERSION}` images. Good for
# kicking the tyres without waiting on a full host build.
demo: ## Run an example stack in Vagrant, no local build (EXAMPLE=prplos|rdk_lxd)
	cd examples/$(EXAMPLE) && vagrant up
	@echo ""
	@echo "Demo stack '$(EXAMPLE)' is up. Forwarded ports are listed in the Vagrantfile."
	@echo "For prplos, the orchestrator REST API is on http://localhost:8080."
	@echo "Teardown:  make demo-down EXAMPLE=$(EXAMPLE)"

demo-down: ## Halt the demo VM (ExecStop / bench-down.sh tears down the stack)
	-cd examples/$(EXAMPLE) && vagrant halt 2>/dev/null || true

smoke-down: ## Tear down the stack and halt the VM (safe anytime)
	-cd $(SMOKE_DIR) && vagrant ssh -c "cd /vagrant && docker compose -f $(COMPOSE_FILE) down -v" 2>/dev/null || true
	-cd $(SMOKE_DIR) && vagrant halt 2>/dev/null || true

smoke-logs: ## Dump orchestrator.log + per-service compose logs from the VM
	@cd $(SMOKE_DIR) && vagrant ssh -c '\
	  cd /vagrant; \
	  echo "===== docker ps -a ====="; \
	  docker ps -a; \
	  echo; echo "===== /var/log/orchestrator.log ====="; \
	  docker exec orchestrator cat /var/log/orchestrator.log 2>&1 || true; \
	  for svc in $$(docker compose -f $(COMPOSE_FILE) config --services); do \
	    echo; echo "===== $$svc logs ====="; \
	    docker compose -f $(COMPOSE_FILE) logs --no-color "$$svc" || true; \
	  done'

# ----- Internal helpers (underscore-prefixed; not for direct use) -----
_smoke_ship:
	@echo "[smoke] saving $(words $(SMOKE_IMAGES)) images to VM..."
	@cd $(SMOKE_DIR) && AUTOSTART=0 vagrant up
	@cd $(SMOKE_DIR) && vagrant rsync
	@$(DOCKER) save \
	  $(foreach i,$(SMOKE_IMAGES),$(REGISTRY)/$(i):$(VERSION)) \
	  | gzip \
	  | (cd $(SMOKE_DIR) && vagrant ssh -c 'gunzip | docker load')

_smoke_compose_up:
	@cd $(SMOKE_DIR) && vagrant ssh -c '\
	  cd /vagrant && \
	  docker compose -f $(COMPOSE_FILE) --env-file .env up -d --pull=missing'

_smoke_probe:
	@cat scripts/smoke-probe.sh \
	  | (cd $(SMOKE_DIR) && vagrant ssh -- 'bash -s') 2>&1 \
	  | tee smoke-probe.log

# ----- Composite -----
all: lint build smoke ## Full local CI: lint + build + smoke
