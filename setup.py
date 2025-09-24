from setuptools import setup, find_packages

setup(
    name="godel_chat_mine",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "selenium>=4.0.0",
    ],
    author="Hayden",
    author_email="haydenwaffles@gmail.com",
    description="A tool to scrape and mine Godel Terminal chat messages",
    entry_points={
        "console_scripts": [
            "godel-chat-mine=godel_chat_mine.chatscraper:main",
        ],
    },
) 