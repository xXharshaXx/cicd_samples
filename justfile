image_name := "assignments-validation"
container_name := "assignments-validation"

rebuild: rm-container build

rm-container:
  docker rm -f {{container_name}}

build: rm-container
  docker build -t {{image_name}} .

run: build
  docker run -d  -p 3010:5001 --name {{container_name}} -it --restart unless-stopped {{image_name}}

watch: run
  docker logs -f {{container_name}}

