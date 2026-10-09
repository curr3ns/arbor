FROM node:24-bookworm-slim
# grove-launch refuses an agent image without these labels: the entrypoint speaks the exchange
# protocol in reference/protocol.md and reaches the network only through the egress socket.
LABEL arbor.grove.egress=socket
LABEL arbor.grove.protocol=1
ARG CLAUDE_CODE_VERSION=2.1.296
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates jq \
 && rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION} && npm cache clean --force
COPY relay.ts /opt/grove/relay.ts
COPY entrypoint.sh /opt/grove/entrypoint.sh
COPY skills /opt/grove/skills
# An empty named volume copies its mount point's ownership on first mount.
RUN chmod 0755 /opt/grove/entrypoint.sh \
 && mkdir -p /workspace /run/grove-egress /exchange/in /exchange/out \
 && chown node:node /workspace /run/grove-egress
USER node
WORKDIR /workspace
ENTRYPOINT ["/opt/grove/entrypoint.sh"]
