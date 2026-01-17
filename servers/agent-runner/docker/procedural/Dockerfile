# Agent Runner with Procedural Executor
#
# Extends agent-runner-base with the procedural executor.
# Executes predefined CLI commands/scripts (non-AI execution).
#
# Build:
#   docker build -t agent-runner-base:latest -f servers/agent-runner/docker/base/Dockerfile .
#   docker build -t agent-runner-procedural:latest \
#     --build-arg BASE_IMAGE=agent-runner-base:latest \
#     -f servers/agent-runner/docker/procedural/Dockerfile .

ARG BASE_IMAGE=agent-runner-base:latest
FROM ${BASE_IMAGE}

# Copy procedural executor
COPY servers/agent-runner/executors/procedural-executor/ /app/servers/agent-runner/executors/procedural-executor/

# Copy compatible profiles (only profiles that use procedural executor)
COPY servers/agent-runner/docker/procedural/profiles/ /app/servers/agent-runner/profiles/

# Default to echo profile (example procedural agent)
ENV PROFILE=echo
