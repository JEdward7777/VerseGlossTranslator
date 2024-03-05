# %% [markdown]
# # Translate Gloss by ChatGPT

# %%
import getpass, json, re, copy, os


host_local = False

if not host_local:
    from openai import OpenAI
else:
    from transformers import pipeline

# %%

if not host_local:
    # see if we can get an openai api key out of a config.json file
    openai_api_key = None
    if os.path.exists("config.json"):
        with open("config.json") as f:
            config = json.load(f)
            if "openai_api_key" in config:
                openai_api_key = config["openai_api_key"]
    if not openai_api_key:
        openai_api_key = getpass.getpass("OpenAI api key?")

# %%
output_language = "English"


# %%
system_message = f"""
You are a language professor preparing language material.  
You are translating subsections of Bible verses from Greek and French into {output_language}.
""".strip()

if not host_local:
    model = "gpt-3.5-turbo"
    #model = "gpt-4"
else:
    hugging_face_model = "teknium/OpenHermes-2.5-Mistral-7B"


# %%
input_data = f"./data/php_ChatGPT_{output_language}.json"
output_filename = f"./data/php_ChatGPT_{output_language}_matched.json"
book_name = "Philippians"

# %%
def strip_and_tokenize_gloss( gloss ):
    gloss = gloss.replace( '-', ' ' ).gloss.replace( '*', ' ' ).strip()

    while '  ' in gloss:
        gloss = gloss.replace( '  ', ' ' )

    tokens_to_nuke = ['.', '?', '!', ',', '"', "'", '(', ')']
    for token in tokens_to_nuke:
        gloss = gloss.replace( token, '' )

    return gloss.split()


def generate_prompt_string( _data, verse_index, chunk_index, gloss_index, _book_name ):
    verse = _data[verse_index]
    chunks = verse['chunks']
    chunk = chunks[chunk_index]
    sources = chunk['source']
    first_piece = sources[0]

    _n = '\n' #f-string objection < python 3.12

    tokenized_gloss = strip_and_tokenize_gloss( chunk['gloss'] )

    return f"""
Look at this verse:
```
{_book_name} {first_piece['cv']}: {verse['sourceString']}
```

Morphology information:
```
{_n.join( str(index) + ": " + source['content'] + ': ' + ','.join(source['morph']) for index, source in enumerate(sources) ) }
```

Focus on these specific source words:
```
{ _n.join( str(index) + ": " + source['content'] for index, source in enumerate(sources) ) }
```

This is the output gloss from the previous translation:
```
{_n.join( str(index) + ': ' + token for index, token in enumerate(tokenized_gloss) ) }
```

Don't mention any of the other source words in your response.

If the word is implicit, say so.

Which source word translates to the word "{gloss_index}: {tokenized_gloss[gloss_index]}" or is it implicit?
""".strip()

# %%
if not host_local:
    client = OpenAI( api_key = openai_api_key )
else:
    pipe = pipeline("text-generation", hugging_face_model)

# %%
def map_gloss_token( _data, verse_index, chunk_index, gloss_index, _book_name ):
    prompt = generate_prompt_string( _data, verse_index, chunk_index, gloss_index, _book_name )
    messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]

    if not host_local:
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        #return response.choices[0].text,
        return response.choices[0].message.content
    else:
        response = pipe(messages, max_new_tokens=128)
        return response[0]['generated_text'][-1]['content']


def extract_answer_from_response( _response, source_words ):
    

    #see if it is a raw list of numbers.
    try:
        return [int(x) for x in _response.split(',') if int(x) >= 0]
    except ValueError:

        #'The word "the" in the English translation is implicit. The Greek source words in this context are "Χριστῷ" (Christ) and "Ἰησοῦ" (Jesus). The word "the" is not directly translated from the Greek source words but is understood in the English sentence structure.'
        implicit_keys = [
            "is implicit", "is implied", "not directly translated from"
        ]
        #if the response includes this then it is an implied word    
        for key in implicit_keys:
            if key in _response:
                return []
        #compile all the quoted text in the response.
        quoted_strings = re.findall(r'"(.*?)"', _response) + re.findall(r"'(.*?)'", _response)

        #also add in the ``` ``` quoted items.`
        quoted_strings += re.findall(r'```(.*?)```', _response, re.DOTALL)

        if quoted_strings:
            quoted_strings = [x.strip().replace('.', '').replace(',', '') for x in quoted_strings]

            #see if any of the source words are exactly in the quoted_strings.
            result = []
            for source_index, source_word in enumerate(source_words):
                if source_word['content'] in quoted_strings:
                    result.append(source_index)
            if result:
                return result
            
            #Now see if the source words with an index on the front is in the quoted_strings.
            result = []
            for source_index, source_word in enumerate(source_words):
                if str(source_index) + ': ' + source_word['content'] in quoted_strings:
                    result.append(source_index)
            if result:
                return result

            #see if any of the source words are in any of the quoted_strings.
            result = []
            for source_index, source_word in enumerate(source_words):
                for quoted_string in quoted_strings:
                    if source_word['content'] in quoted_string:
                        result.append(source_index)
            if result:
                return result
            

            #see if any of the quoted_strings are indexes.
            result = []
            for source_index, source_word in enumerate(source_words):
                for quoted_string in quoted_strings:
                    if str(source_index) == quoted_string:
                        result.append(source_index)
            if result:
                return result
            
        #see if the words are in the response loose with an index
        result = []
        for source_index, source_word in enumerate(source_words):
            if str(source_index) + ': ' + source_word['content']  in _response:
                result.append(source_index)
        if result:
            return result

        #see if any of the source words are in the response but not quoted.
        result = []
        for source_index, source_word in enumerate(source_words):
            if source_word['content'] in _response:
                result.append(source_index)
        if result:
            return result

    raise ValueError("Result not in expected format.")



# %%
def number_of_verses( _data ):
    return len(_data)
def number_of_chunks( _data, verse_index ):
    return len(_data[verse_index]['chunks'])

def number_of_gloss_tokens( _data, verse_index, chunk_index ):
    chunk = _data[verse_index]['chunks'][chunk_index]
    return len( strip_and_tokenize_gloss( chunk['gloss'] ) )
# %%
#go ahead and load the data.
with open( input_data, 'r' ) as fin:
    data = json.load( fin )
# %%
output_data = copy.deepcopy(data)

verse_index = 0
chunk_index = 0 #TODO: make sure this is zero.
gloss_index = 0
# %%

#append to match_process.log
with open( "match_process.log", "a" ) as fout:
    done = False

    while not done:

        if gloss_index >= number_of_gloss_tokens(data, verse_index, chunk_index):
            done = True

        if not done:
            fout.write( f"Processing verse {verse_index} chunk {chunk_index}\n" )
            fout.write( f"Prompt string:\n{generate_prompt_string( data, verse_index, chunk_index, gloss_index, book_name )}\n\n")

            response = map_gloss_token( data, verse_index, chunk_index, gloss_index, book_name )

            fout.write( f"Response:\n{response}\n\n" )

            answer = extract_answer_from_response( response, data[verse_index]['chunks'][chunk_index]['source'] )

            fout.write( f"Answer:\n{answer}\n\n" )
            fout.flush()

            if 'gloss_mapping' not in output_data[verse_index]['chunks'][chunk_index]:
                output_data[verse_index]['chunks'][chunk_index]['gloss_mapping'] = {}

            gloss_tokenized = strip_and_tokenize_gloss( output_data[verse_index]['chunks'][chunk_index]['gloss'] )
            source_words = output_data[verse_index]['chunks'][chunk_index]['source']
            output_data[verse_index]['chunks'][chunk_index]['gloss_mapping'][ f"{gloss_index}: {gloss_tokenized[gloss_index]}" ] = [f"{index}: {source_words[index]['content']}" for index in answer]

            fout.write( "gloss_mapping:\n" )
            fout.write( json.dumps( output_data[verse_index]['chunks'][chunk_index]['gloss_mapping'], indent=4 ) )
            fout.write( "\n\n" )
            fout.flush()

            #update the indexes
            gloss_index += 1

            if gloss_index >= number_of_gloss_tokens(data, verse_index, chunk_index):
                chunk_index += 1
                gloss_index = 0

            if chunk_index >= number_of_chunks(data, verse_index):
                verse_index += 1
                chunk_index = 0



# %%
with open( output_filename, 'w' ) as fout:
    fout.write( json.dumps( output_data, indent=4 ) )

# %%


