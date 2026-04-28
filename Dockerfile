FROM docker.arvancloud.ir/python:3.11.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --trusted-host https://package-mirror.liara.ir -i https://package-mirror.liara.ir/repository/pypi/ --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "trainer/train.py"]