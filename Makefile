# Makefile — raikou-net build / lint / smoke / push entry point.
#
# Build matrix lives in docker-bake.hcl. This Makefile is a thin wrapper:
# build/push delegate to `docker buildx bake`; smoke wraps Vagrant; lint
# wraps pre-commit; bump rewrites the VERSION file and example .env files.
#
# Usage: `make help`.

.DEFAULT_GOAL := help
SHELL         := /bin/bash

# ----- Configuration (override on CLI: `make push VERSION=v4`) -----
GHCR_REGISTRY ?= ghcr.io/ketantewari/raikou
VERSION       ?= $(shell cat VERSION 2>/dev/null || echo v3)
LATEST        ?= yes
DOCKER        ?= docker
COMPOSE_FILE  ?= docker-compose.ghcr.yaml

# These names are picked up by docker-bake.hcl's `variable` blocks.
export VERSION
export LATEST
export REGISTRY := $(GHCR_REGISTRY)

# Image targets — names match bake target names verbatim. The push-set
# (images that get GHCR tags) is declared inside docker-bake.hcl as the
# `push-set` group; this Makefile delegates to bake for `make push` and
# doesn't need to duplicate the membership list.
IMAGES := orchestrator ssh router wan lan dhcp ntp cpe acs sipcenter sipphone router-ethernet

.PHONY: help lint build build-orchestrator build-components $(IMAGES) bump push clean

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
	  $(DOCKER) rmi "$(GHCR_REGISTRY)/$$img:$(VERSION)" 2>/dev/null || true; \
	  $(DOCKER) rmi "$(GHCR_REGISTRY)/$$img:latest"    2>/dev/null || true; \
	done

# NOTE: smoke targets and a composite `all` target are added by Task 5,
# once scripts/smoke-probe.sh exists. Keeping this Makefile self-contained
# until then.
