# Minimal image for running zsp in CI or on machines without Python.
#
#   docker build -t zsp .
#   docker run --rm -it -v "$HOME/.config/zsp:/root/.config/zsp" zsp items

FROM python:3.12-slim AS build

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir build \
 && python -m build --wheel --outdir /dist


FROM python:3.12-slim

LABEL org.opencontainers.image.title="zsp" \
      org.opencontainers.image.description="Command-line client for Zoho Sprints" \
      org.opencontainers.image.source="https://github.com/sudoSharun/zsp" \
      org.opencontainers.image.licenses="MIT"

COPY --from=build /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl

# Credentials are expected to be bind-mounted from the host; `zsp login`
# needs a browser, so authenticate outside the container.
VOLUME ["/root/.config/zsp"]

ENTRYPOINT ["zsp"]
CMD ["--help"]
