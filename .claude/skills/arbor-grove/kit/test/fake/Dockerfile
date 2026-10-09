# The agent image with `claude` replaced by a stub, for the end-to-end test only.
FROM arbor-grove-agent:latest
USER root
COPY claude /usr/local/bin/claude
RUN chmod 0755 /usr/local/bin/claude
USER node
