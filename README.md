# Godel Chat Mine

A tool to scrape chat messages from the Godel Terminal platform with real-time logging capabilities. Data processing and sentiment analysis in development.

Chat logs can be found in chat_logs folder as MASTER_LOG.json and inception_to9-23.json

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd godel_chat_mine

# Install the package
pip install -e .
```

## Usage

### As a command-line tool

Make your own config.py using config.template. Save your godel username and password as well as file directory to store the logs.

After installation, you can run the tool directly from the command line:

```bash
chatscraper.py
```


## Features

- Login to Godel Terminal
- Navigate to specific chat rooms (currently just general)
- Extract chat messages with timestamps and usernames
- Send messages to the chat
- **Real-time message logging** - each new message is saved to disk immediately
- Automatic log file creation with timestamps
- Crash-resistant - data is saved continuously to prevent data loss
- Customizable log directory

## Dependencies

- Python 3.6+
- Selenium 4.0.0+
- Chrome WebDriver

## License

MIT 
