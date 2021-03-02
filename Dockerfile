FROM python:3.7

RUN cat /etc/apt/sources.list | awk -F[/:] '{print $4}' | sort | uniq | grep -v "^$" | xargs -I{} sed -i 's|{}|mirrors.aliyun.com|g' /etc/apt/sources.list && \
    apt update && \
    apt install -y psmisc netcat wait-for-it && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip3 install -i https://mirrors.aliyun.com/pypi/simple -r requirements.txt

COPY . .

WORKDIR /app/wechat-spider

EXPOSE 8080
EXPOSE 8081

# ENTRYPOINT [ "python3", "./run.py" ]

CMD [ "python3", "./run.py" ]