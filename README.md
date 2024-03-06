# VerseGlossTranslator

![VerseGlossTranslator Logo](./data/logo.jpeg)

VerseGlossTranslator is a project aimed at translating Bible passages from Greek to French using juxtalinear approach, and then translating from Greek to English utilizing the OpenAI's GPT model (ChatGPT). 

## Installation

Before using VerseGlossTranslator, ensure you have the OpenAI client installed. You can install it via pip:

```bash
pip install openai
```

Additionally, you will need an OpenAI API key. Make sure to set up your API key following the instructions provided by OpenAI.

## Usage

1. Edit the variables at the beginning of `TranslateGlossChatGPT.py` to specify the input data, book name, and the OpenAI model to be used.
2. Run the script `TranslateGlossChatGPT.py` to perform the translations.
3. To generate HTML files, run `ConvertToHtml.py`.

## Prerequisites

- OpenAI API key
- OpenAI Python client (`openai`), installed via pip

## Contributing

Contributions to VerseGlossTranslator are welcome! If you have any ideas, suggestions, or bug fixes, please feel free to open an issue or create a pull request.

## License

This project is licensed under the MIT License.