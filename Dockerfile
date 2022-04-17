FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul

RUN apt-get update -y
RUN apt-get install -y tzdata
RUN apt-get install python3 -y
RUN apt-get install python3-pip -y
RUN apt-get install wget -y
RUN python3 -m pip install selenium
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - 
RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
RUN apt-get update -y
# version check required
RUN apt-get install google-chrome-stable -y
RUN pip3 install tqdm
RUN pip3 install requests
RUN apt-get install vim -y

ENV PATH=$PATH:/app

WORKDIR /app
