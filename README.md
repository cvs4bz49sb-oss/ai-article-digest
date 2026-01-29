# AI Article Digest Generator

A command-line tool that scrapes articles from websites and generates intellectually rigorous summaries in the Mere Orthodoxy Digest style using Claude AI.

## Features

- **Web Scraping**: Extracts article titles, authors, and content from various website structures
- **AI Summarization**: Uses Claude to generate thoughtful, argument-focused summaries
- **Editorial Voice**: Produces summaries with sophisticated vocabulary and intellectual depth
- **Flexible Output**: Display to console or save to file

## Installation

1. Clone or download this project

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your API key:
```bash
cp .env.example .env
```
Then edit `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=your-api-key-here
```

## Usage

### Basic Usage

```bash
python digest_generator.py https://example-blog.com
```

### Specify Number of Articles

```bash
python digest_generator.py https://example-blog.com -n 5
```

### Save Output to File

```bash
python digest_generator.py https://example-blog.com -o digest.md
```

### Verbose Mode

```bash
python digest_generator.py https://example-blog.com -v
```

### All Options

```bash
python digest_generator.py --help
```

```
Usage: digest_generator.py [OPTIONS] URL

  Generate an article digest from a website.

  URL: The website URL to scrape articles from.

Options:
  -n, --count INTEGER  Number of articles to process (default: 10)
  -o, --output PATH    Save output to a file (optional)
  -v, --verbose        Show detailed progress information
  --help               Show this message and exit.
```

## Output Format

The generated digest includes:

1. **Headline**: A compelling headline using the most interesting articles
2. **Combined Summary**: A single sentence incorporating all articles
3. **Individual Summaries**: Numbered list with:
   - Bold article title
   - Italicized author name
   - 50-word maximum summary

### Example Output

```
The Death of Institutional Trust and What Comes Next

This week's articles examine the fracturing of institutional authority, from
religious organizations to political parties, and explore how communities
might rebuild shared meaning in an age of pervasive skepticism.

Articles

1. **The End of the Megachurch Era**
*John Smith*
The megachurch model's decline reflects not merely changing consumer preferences
but a deeper crisis of Protestant ecclesiology. When churches compete through
amenities rather than doctrine, they inadvertently teach congregants that
religious commitment is transactional—a lesson that ultimately undermines
their own institutional authority.

2. **Why Young Voters Distrust Both Parties**
*Jane Doe*
Political alienation among young voters stems not from apathy but from a
coherent critique: both parties prioritize donor interests over constituents.
This isn't cynicism but clear-eyed recognition that electoral politics operates
within constraints that systematically exclude their concerns.
```

## Style Guide

The summaries are generated to match these characteristics:

- **Intellectually Rigorous**: Sophisticated vocabulary, complex ideas
- **Argument-Focused**: Presents what authors contend, not just topics
- **Non-Therapeutic**: Analytical rather than emotional language
- **Principled**: Connects contemporary issues to deeper foundations
- **Precise**: Every word earns its place

## Configuration

Edit `config.py` to customize:

- `CLAUDE_MODEL`: The Claude model to use
- `DEFAULT_ARTICLE_COUNT`: Default number of articles
- `MAX_SUMMARY_WORDS`: Maximum words per summary
- `ARTICLE_SELECTORS`: CSS selectors for scraping different website structures

## Troubleshooting

### "No article links found"

The website structure may not match common patterns. You can customize the selectors in `config.py` to match the specific website.

### API Key Issues

Make sure your `.env` file contains a valid Anthropic API key and the file is in the same directory as the script.

### Rate Limiting

If you encounter rate limits, reduce the number of articles or wait before retrying.

## Project Structure

```
ai-article-digest/
├── digest_generator.py   # Main CLI application
├── scraper.py            # Web scraping module
├── summarizer.py         # Claude API integration
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── .env.example          # Example environment file
└── README.md             # This file
```

## License

MIT License
