CONTAINER_NAME=my-running-bot
IMAGE_NAME=my-bot

docker build --no-cache -t $IMAGE_NAME .

if docker ps --format '{{.Names}}' | grep -qw $CONTAINER_NAME; then
    echo "Container $CONTAINER_NAME is already running. Stopping and removing..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
    echo "Container removed."
else
    echo "No running container named $CONTAINER_NAME. Proceeding..."
fi

sleep 1
docker run -itd --rm --name $CONTAINER_NAME $IMAGE_NAME
