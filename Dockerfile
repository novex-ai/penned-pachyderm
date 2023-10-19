FROM ubuntu:jammy-20231004

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update \
  && apt upgrade -y \
  && apt install -y build-essential checkinstall wget \
  && apt clean \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# https://devguide.python.org/getting-started/setup-building/#install-dependencies
RUN apt update \
  && apt install -y \
    gdb lcov pkg-config \
    libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev \
    libncurses5-dev libreadline6-dev libsqlite3-dev libssl-dev \
    lzma lzma-dev tk-dev uuid-dev zlib1g-dev \
  && apt clean \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN wget https://www.python.org/ftp/python/3.11.6/Python-3.11.6.tgz \
  && tar -xzf Python-3.11.6.tgz \
  && cd Python-3.11.6 \
  && ./configure --enable-optimizations \
  && make -j $(nproc) \
  && make altinstall \
  && cd .. \
  && rm -rf Python-3.11.6 Python-3.11.6.tgz

RUN update-alternatives --install /usr/bin/python python /usr/local/bin/python3.11 1 \
  && update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.11 1 \
  && pip3.11 install --upgrade pip \
  && update-alternatives --install /usr/bin/pip pip /usr/local/bin/pip3.11 1 \
  && update-alternatives --install /usr/bin/pip3 pip3 /usr/local/bin/pip3.11 1

WORKDIR /sanic

COPY ["run_server.py", "requirements.txt", "./"]
COPY frontend_quasar_vue/dist frontend_quasar_vue/dist/
COPY backend_sanic/ backend_sanic/

RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["python", "run_server.py"]