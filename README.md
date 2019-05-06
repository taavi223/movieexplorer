# MovieExplorer

MovieExplorer is a tool that allows you to **explore and navigate the cinematic universe**. Use it to find a movie you're in the mood for right now, to browse movies that match a particular interest, or to explore new genres and tastes!

MovieExplorer was originally developed for by [Taavi Taijala](https://taavi.taijala.com/) as part of a research study on [MovieLens](https://movielens.org/). A paper examining user perceptions and usage of the tool was published at the _Symposium on Applied Computing_ in 2018. The tool is archived here for public use. To learn more about MovieExplorer or download the paper, please visit the [author's website](https://taavi.taijala.com/).

## Requirements

- Python 3.7.2+ (not tested with earlier versions, but may still work)
- virtualenv (highly recommended)

## Installation

It is highly recommended that install this project and it's dependencies into a newly-created virtualenv to avoid incompatibilities and other issues. If you are using a virtualenv, make sure it's been activated before running any of the following commands.

To install dependencies, run `pip3 install -r requirements.txt` from the root project directory. 

## Running MovieExplorer

In one terminal window, run:

```
cd api
python3 app.py
```

In another terminal window, run:

```
python3 demo.py
```

You should now be able to visit `localhost:8000` in your browser and use MovieExplorer.

Please note that an internet connection is required to load movie thumbnails and trailers.