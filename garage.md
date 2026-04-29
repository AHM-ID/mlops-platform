```bash
podman exec mlops-platform_garage_1 /garage status

podman exec mlops-platform_garage_1 /garage layout assign <NODE_ID> -z zone1 -c 1

podman exec mlops-platform_garage_1 /garage layout apply --version 1

podman exec mlops-platform_garage_1 /garage key new --name admin

podman exec mlops-platform_garage_1 /garage bucket allow --read --write --key <KEY_ID> mlflow

## .env file
AWS_ACCESS_KEY_ID=<the-access-key-id-from-step-5>
AWS_SECRET_ACCESS_KEY=<the-secret-key-from-step-5>

podman exec mlops-platform_garage_1 /garage key list
podman exec mlops-platform_garage_1 /garage bucket list

podman-compose restart mlflow
podman-compose stop trainer
podman-compose rm -f trainer
podman-compose --env-file .env up trainer
podman-compose restart api
podman-compose restart nginx
```
