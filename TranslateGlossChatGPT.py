# %% [markdown]
# # Translate Gloss by ChatGPT

# %%
import getpass, json, re, copy, os
from openai import OpenAI

# %%
# see if we can get an openai api key out of a config.json file
openai_api_key = None
if os.path.exists("config.json"):
    with open("config.json") as f:
        config = json.load(f)
        if "openai_api_key" in config:
            openai_api_key = config["openai_api_key"]

# %%
if not openai_api_key:
    openai_api_key = getpass.getpass("OpenAI api key?")

# %%
output_language = "English"

# %%
def generate_prompt_string( _data, verse_index, chunk_index, _book_name ):
    verse = _data[verse_index]
    chunks = verse['chunks']
    chunk = chunks[chunk_index]
    sources = chunk['source']
    first_piece = sources[0]

    return f"""
Look at this verse:
{_book_name} {first_piece['cv']}: {verse['sourceString']}

Focus on these specific words:
{' '.join(source['content'] for source in sources)}

The gloss for this in French is:
{chunk['gloss']}

What is the gloss for this in {output_language}?
""".strip()

# %%
system_message = f"""
You are a language professor preparing language material.  
You are translating subsections of Bible verses from Greek and French into {output_language}.
""".strip()
model = "gpt-3.5-turbo"

# %%
input_data = "./data/php_21.01.2024.json"
output_filename = "./data/php_ChatGPT_English.json"
book_name = "Philippians"

# %%
#go ahead and load the data.
with open( input_data ) as fin:
    data = json.loads( fin.read() )

# %%
def generate_prompt_string( _data, verse_index, chunk_index, _book_name ):
    verse = _data[verse_index]
    chunks = verse['chunks']
    chunk = chunks[chunk_index]
    sources = chunk['source']
    first_piece = sources[0]

    return f"""
Look at this verse:
```
{_book_name} {first_piece['cv']}: {verse['sourceString']}
```

Focus on these specific words:
```
{' '.join(source['content'] for source in sources)}
```

The gloss for this in French is:
```
{chunk['gloss']}
```

What is the gloss for this in {output_language}?  Mark added words not found the Greek but needed by {output_language} with *asterisks*. Output the answer in JSON.
""".strip()

# %%
print( generate_prompt_string( data, 0, 0, book_name ) )

# %%
client = OpenAI( api_key = openai_api_key )
def generate_gloss_for( _data, verse_index, chunk_index, _book_name ):
    prompt = generate_prompt_string( _data, verse_index, chunk_index, _book_name )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
    )
    #return response.choices[0].text,
    return response

# %%

def extract_answer_from_response( _response ):
    #This checks to see if it is in a MarkDown block.
    extractor_regular_expression = r"```(?:json)?(?P<json_data>.*?)```"
    match = re.search(extractor_regular_expression, _response.choices[0].message.content, re.DOTALL)

    if not match:
        #This one checks for just raw json
        extractor_regular_expression = r"(?P<json_data>\{.*\})"
        match = re.search(extractor_regular_expression, _response.choices[0].message.content, re.DOTALL)

        if not match:
            raise ValueError("Result not in expected format.")

    extracted_data = match.group('json_data')

    #now parse the json.
    response = json.loads(extracted_data)

    #see if we can find a reference to output_language
    for key, value in response.items():
        if output_language.lower() in key.lower():
            return value

    raise ValueError("Result not in expected format.")   

# %%
test_verse_index = 0
test_chunk_index = 0

# %%

test_response = generate_gloss_for( data, test_verse_index, test_chunk_index, book_name )

print( extract_answer_from_response( test_response ) )

# %%
def number_of_verses( _data ):
    return len(_data)
def number_of_chunks( _data, verse_index ):
    return len(_data[verse_index]['chunks'])

print( f"Number of verses: {number_of_verses(data)}" )
print( f"Number of chunks in {test_verse_index}: {number_of_chunks(data, test_verse_index)}" )

# %%
test_response

# %%
output_data = copy.deepcopy(data)

for verse_index in range(0, number_of_verses(data)):
    for chunk_index in range(0, number_of_chunks(data, verse_index)):
        response = generate_gloss_for( data, verse_index, chunk_index, book_name )
        answer = extract_answer_from_response( response )
        output_data[verse_index]['chunks'][chunk_index]['gloss'] = answer

# %%
with open( output_filename, 'w' ) as fout:
    fout.write( json.dumps( output_data ), indent=4 )

# %%



