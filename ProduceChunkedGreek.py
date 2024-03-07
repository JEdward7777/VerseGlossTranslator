# %%
import glob, json, os
import xml.etree.ElementTree as ET

# %%
# https://github.com/Clear-Bible/macula-greek/blob/main/Nestle1904/nodes/
greek_nodes_glob = "../macula-greek/Nestle1904/nodes/*.xml"
output_directory = "./data/"

trim_num_leaves = 3
string_num_leaves = 4

# %%
input_filenames = glob.glob( greek_nodes_glob )
# %%

test_filename = input_filenames[-4]
# %%

#need to figure out at what level are 3 to 4 leaves.
def count_leaves( node ):
    if len( node ) == 0:
        return 1
    else:
        return sum( count_leaves( child ) for child in node )
    
def max_depth( node ):
    if len( node ) == 0:
        return 1
    else:
        return max( max_depth( child ) for child in node ) + 1
    
# %%
def average_leaves_below_depth( node, depth ):
    if depth == 0:
        return count_leaves( node )
    else:
        sum_ = 0
        for child in node:
            sum_ += average_leaves_below_depth( child, depth - 1 )
        if len( node ) > 0:
            return sum_ / len( node )
        else:
            return 0

# %%
        
def is_list_of_list( result ):
    if isinstance( result, list ) and isinstance( result[0], list ):
        return True
    return False

# %%
def harvest_at_floating_depth( node, target_num_leaves ):
    child_results = [harvest_at_floating_depth( child, target_num_leaves ) for child in node]

    #if this is at the bottom return self.
    if len( child_results ) == 0:
        return [node]

    #now see if any of the children are a list of a list, in which case they all need to be.
    have_list_of_list = False
    for child_result in child_results:
        if is_list_of_list(child_result):
            have_list_of_list = True
            break
    if have_list_of_list:
        result = []
        for child_result in child_results:
            if is_list_of_list( child_result ):
                result.extend( child_result )
            else:
                result.append( child_result )
        return result
    
    #now see if any of our children are longer than the target.
    have_longer = False
    for child_result in child_results:
        if len( child_result ) >= target_num_leaves:
            have_longer = True
            break
    #if we have longer, then our result is the child_results,
    #because that converts it into a list of lists.
    if have_longer:
        return child_results
    

    #In the last case we just need to concat the results
    result = []
    for child_result in child_results:
        result.extend( child_result )
    return result

def clump_singles( data, target_length ):
    #first make sure the data is all lists, so wrap anything in a list which isn't.
    for index, chunk in enumerate( data ):
        if not isinstance( chunk, list ):
            data[index] = [chunk]


    #iterate through the list backwards
    #and if we see a single, then add it to what comes after it
    #if what comes after it is not greater then the target length.
    output_list_reversed = []

    for chunk in reversed(data):
        if len( output_list_reversed ) == 0:
            output_list_reversed.append( chunk[:] )
        elif len( chunk ) == 1:
            if len(output_list_reversed[-1]) < target_length:
                output_list_reversed[-1].insert( 0, chunk[0] )
            else:
                output_list_reversed.append( chunk[:] )
        else:
            output_list_reversed.append( chunk[:] )

    return list( reversed( output_list_reversed ) )


# %%

# %%
#now I want to print out the chunks.
def print_chunks( chunked_results ):
    for index, chunk in enumerate( chunked_results ):
        print( f"{index}:", end=" " )
        for piece in chunk:
            print( piece.text, end=" " )
        print()
    
def print_chunked_sentences( chunked_sentences ):
    for sentence in chunked_sentences:
        print( sentence['text'] )
        print_chunks( sentence['chunks'] )

def get_text( node ):
    if len( node ) == 0:
        return node.text
    else:
        return " ".join( get_text( child ) for child in node )
    
def get_leaves( node ):
    if len( node ) == 0:
        yield node
    else:
        for child in node:
            yield from get_leaves( child )
    
def sort_nodes( nodes ):
    def location_key( node ):
        x = node.attrib['ref']
        book, x = x.split( " " )
        chapter, x = x.split(":")
        verse, index = x.split( "!" )
        return int(chapter),int(verse),int(index)
    return sorted( nodes, key=location_key )
        

# %%
def filename_to_chunked_sentences( filename ):
    tree = ET.parse(filename)
    root = tree.getroot()

    chunked_sentences = []
    for sentence in root:
        leaves = list( get_leaves( sentence ) )
        sorted_leaves = sort_nodes( leaves )
        text = get_text( sorted_leaves ) 
        #print_chunks( [leaves, sorted_leaves] )
        chunked_sentence = clump_singles(harvest_at_floating_depth( sentence, trim_num_leaves ), string_num_leaves)
        chunked_sentence_object = {
            "text": text,
            "chunks": chunked_sentence
        }
        #print_chunked_sentences( [chunked_sentence_object] )
        chunked_sentences.append(chunked_sentence_object)
    return chunked_sentences

# %%

def transform_source( source ):
    result = {
        "content": source.text,
        "lemma": [source.attrib['UnicodeLemma']],
        "strong": [source.attrib['StrongNumber']],
        #"morph": [], #The Clear information has a morphid which isn't the same.
        "cv": source.attrib['ref'].split(" ")[-1].split( "!" )[0]
    }
    #The Clear strong number doesn't have a G on the front of it.
    if not result["strong"][0].startswith( "G" ): result["strong"][0] = "G" + result["strong"][0]
    return result

def transform_chunk( chunk ):
    result = {
        "source": [transform_source( source ) for source in chunk],
        "gloss": "<not implemented>",
    }
    return result

def transform_sentence( sentence ):
    result = {
        "chunks": [transform_chunk( chunk ) for chunk in sentence["chunks"]],
        "sourceString": sentence["text"],
    }
    return result
    

# %%
def convert_file( in_filename, out_filename ):
    chunked_sentences = filename_to_chunked_sentences( in_filename )
    converted_chunked_sentences = [transform_sentence( sentence ) for sentence in chunked_sentences]
    with open( out_filename, 'w', encoding='utf-8') as fout:
        json.dump( converted_chunked_sentences, fout, indent=2, ensure_ascii=False )

# %%
#iterate over all the files.
for input_filename in input_filenames:
    base_name = os.path.basename( input_filename )
    base_name_without_extension = os.path.splitext( base_name )[0]
    output_name = f"auto_{base_name_without_extension}.json"
    output_filename = os.path.join( output_directory, output_name )

    convert_file( input_filename, output_filename )

print( "Done" )