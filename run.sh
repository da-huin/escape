docker build --tag escape .
docker run -d -it --rm --name escape -v $PWD:/app escape python3 index.py --theme-name="[강남] 링" --important-datetimes="2022-04-30,2022-05-01"
