# Dockerfile
FROM python:3.9-slim
# FROM jlesage/firefox

WORKDIR /app

# ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    firefox \   
    && rm -rf /var/lib/apt/lists/*

# Get gecko driver
ENV GECKO_VERSION=0.34.0
ADD https://github.com/mozilla/geckodriver/releases/download/v${GECKO_VERSION}/geckodriver-v${GECKO_VERSION}-linux64.tar.gz /geckodriver-v${GECKO_VERSION}-linux64.tar.gz
RUN tar -xvzf /geckodriver-v${GECKO_VERSION}-linux64.tar.gz -C /usr/local/bin  
ENV PATH=/usr/local/bin:$PATH

COPY app.py /app
COPY zetkin.py /app
COPY sms.py /app
COPY requirements.txt /app

RUN pip3 install -r requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]