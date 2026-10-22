# One Linux/RTX image; separate Python environments isolate dependency pins.
FROM python:3.11.11-slim-bookworm
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 PYTHONNOUSERSITE=1
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential cmake ffmpeg libgl1 libegl1 libglib2.0-0 libgomp1 libx11-6 libxext6 libxrender1 libxi6 libxrandr2 libxcursor1 libxinerama1 libsm6 libice6 libvulkan1 libnss3 libasound2 libxt6 libglu1-mesa ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements/constraints.txt /opt/constraints.txt
ENV PIP_CONSTRAINT=/opt/constraints.txt
ARG EXPRESSIVE_COMMIT=a66e910d53da0d90eae845d35aad7c9eb2ae4a04
RUN git clone https://github.com/ATR-Lab/expressive-motion.git /opt/pipeline && git -C /opt/pipeline checkout "$EXPRESSIVE_COMMIT" && git -C /opt/pipeline submodule update --init --recursive external/GMR
# Both stages use the same pinned Torch/CUDA stack. Install it once rather than
# duplicating several GB of GPU libraries; stage-specific packages stay in venvs.
RUN python -m pip install 'numpy==1.26.4' && python -m pip install torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu128
RUN python -m venv --system-site-packages /opt/gvhmr && python -m venv --system-site-packages /opt/gmr
RUN /opt/gvhmr/bin/pip install 'setuptools<81' wheel toml cython 'numpy==1.26.4' && /opt/gvhmr/bin/pip install --no-build-isolation chumpy==0.70 && /opt/gvhmr/bin/pip install --no-build-isolation 'gvhmr[preproc]==1.6.1'
RUN /opt/gmr/bin/pip install 'setuptools<81' wheel toml cython 'numpy==1.26.4' && /opt/gmr/bin/pip install --no-build-isolation chumpy==0.70 && /opt/gmr/bin/pip install --no-build-isolation -e /opt/pipeline/external/GMR 'numpy==1.26.4'
# Fail the build on inconsistent Python dependencies; no checkpoints in the image.
RUN /opt/gvhmr/bin/pip check && /opt/gmr/bin/pip check
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/python", "/workspace/scripts/workshop.py"]
CMD ["--help"]
