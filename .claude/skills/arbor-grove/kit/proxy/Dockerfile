FROM node:24-bookworm-slim
# grove-launch refuses an egress image without this label.
LABEL arbor.grove.egress=socket
WORKDIR /opt/grove/proxy
COPY package.json proxy.ts main.ts ./
# The per-agent sock volume mounts here; an empty volume copies this ownership on first mount.
RUN mkdir -p /run/grove-egress && chown node:node /run/grove-egress
USER node
CMD ["node", "main.ts"]
