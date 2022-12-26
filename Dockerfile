FROM python:3.9-slim

RUN mkdir -p /app
COPY . app.py /app/
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 8080
CMD ["app.py"]
ENTRYPOINT [ "python" ]