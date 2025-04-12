"""
Module: document_processor.py

The script provides entity query of papers from preprocessed information stored in a SQLite database via command-line interface.
It converts the paper PDF files to DOCX format, extracts entities from the text using NLP and stores the results in a SQLite database.
"""

import os
from os.path import exists
from pathlib import Path
import json
import sqlite3
import logging

import openpyxl
import docx
from docx.opc.exceptions import PackageNotFoundError
from pdf2docx import parse
from simplify_docx import simplify
import spacy
import torch
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter

# Constants for file paths and configurations
SOURCE_PATH = "Papers/"
DOCS_PATH = "Docs/"
JSON_PATH = "JSON/"
ENTS_PATH = "Ents/"
DB_FILE = "data/test_db.sqlite"
MAX_TOKEN_LENGTH = 512

# Configure logging
logging.basicConfig(level=logging.INFO)


def get_database_connection(db_file):
    """
    Create a database connection to a SQLite database.

    :param db_file: str, path to the SQLite database file.
    :returns: sqlite3.Connection: A connection object to the SQLite database.
    """
    return sqlite3.connect(db_file)


def load_paper_index(xlsx_path):
    """
    Load paper index from given path.

    :param path to Excel file.
    :returns: list of dictionaries containing the information of papers to precess.
    """
    workbook = openpyxl.load_workbook(xlsx_path, data_only=True)
    index_sheet = workbook['Sheet1']
    headers = [cell.value.strip() for cell in index_sheet[1]]
    papers_to_process = []

    for row in index_sheet.iter_rows(min_row=2):  # Ignore header row
        # Create a dictionary for each row with headers as keys
        row_dict = {key: cell.value for key, cell in zip(headers, row)}
        logging.info(f"Processed row: {row_dict}")

        # Construct file paths
        row_dict['paper_docx'] = os.path.join(DOCS_PATH, row_dict['paper_pdf'] + '.docx')
        row_dict['paper_json'] = os.path.join(JSON_PATH, row_dict['paper_pdf'] + '.json')
        row_dict['paper_entities'] = os.path.join(ENTS_PATH, row_dict['paper_pdf'] + '.json')
        row_dict['paper_pdf'] = os.path.join(SOURCE_PATH, row_dict['paper_pdf'])
        papers_to_process.append(row_dict)

    return papers_to_process


def setup_database(conn):
    """
    Create tables: papers, entities and papers_have_entities

    :param conn: connection to a SQLite database
    """
    cur = conn.cursor()
    # Create 'papers' table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            paper_id INTEGER PRIMARY KEY,
            paper_name TEXT NOT NULL UNIQUE,
            paper_pdf TEXT NOT NULL,
            paper_docx TEXT NOT NULL,
            paper_json TEXT NOT NULL,
            paper_entities TEXT NOT NULL
        );
    """)
    # Create 'entities' table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            entity_id INTEGER PRIMARY KEY,
            entity_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            UNIQUE(entity_name, entity_type)
        );
    """)
    # Create 'papers_have_entities' table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS papers_have_entities (
            entity_id INTEGER,
            paper_id INTEGER,
            count INTEGER DEFAULT 1,
            FOREIGN KEY(entity_id) REFERENCES entities(entity_id),
            FOREIGN KEY(paper_id) REFERENCES papers(paper_id),
            PRIMARY KEY(entity_id, paper_id)
        );
    """)


def load_nlp_model():
    """
    Load the spaCy NLP model.

    :returns: spacy.Language: loaded spaCy NLP model.
    """
    return spacy.load("en_core_web_trf")


def process_documents(papers_to_process, nlp_model, conn):
    """
    Process files_to_proces in source_path by implementing named entity recognitnion via nlp and updating
    tables in the database.

    :param papers_to_process: list of dictionaries containing the information of papers to precess
    :param nlp_model: spaCy NLP model
    :param conn: connection to SQLite database
    """
    cur = conn.cursor()
    processed_files = []

    for paper in papers_to_process:
        process_single_document(paper, nlp_model, cur)
        processed_files.append(paper['paper_pdf'])

    logging.info(f"Processed files: {processed_files}")
    conn.commit()


def process_single_document(paper, nlp_model, cur):
    """
    Process a paper in the form of docx and extracts entities from the full text,
    stores the results in JSON and the database

    :param file_dict: name, pdf, docx, json files and entities of a file
    :param nlp_model: NLP processing module from spaCy
    :param cur: connection cursor
    """
    pdf_file = paper['paper_pdf']
    docx_file = paper['paper_docx']
    json_file = paper['paper_json']
    entities_file = paper['paper_entities']

    # Convert PDF to DOCX if the DOCX file doesn't exist
    if not exists(docx_file):
        parse(pdf_file, docx_file)

    # Load DOCX file
    doc = docx.Document(docx_file)

    # Simplify DOCX and save as JSON
    if not exists(json_file):
        simplified_doc = simplify(doc, {"special-characters-as-text": False})
        with open(json_file, 'w') as output_json:
            json.dump(simplified_doc, output_json)

    # Extract full text from the document
    full_text_array = [para.text for para in doc.paragraphs]

    # Extract entities and save to JSON
    if not exists(entities_file):
        entities = extract_entities(full_text_array, nlp_model)
        with open(entities_file, 'w') as output_entities:
            json.dump(entities, output_entities)
    else:
        with open(entities_file, 'r') as entities_file_obj:
            entities = json.load(entities_file_obj)

    # Update database with the extracted entities
    update_database(cur, paper, entities)

    # Clear GPU cache if using CUDA
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def extract_entities(full_text_array, nlp_model):
    """
    Extract entities from the full text using spaCy NLP model

    :param full_text_array: list of text paragraphs
    :param nlp_model: spaCy NLP model

    :returns:dictionary containing information(text, start_char, end_char, label)
    of extracted entities
    """
    full_text = ''.join(full_text_array)
    doc_tokens = nlp_model.tokenizer(full_text)
    num_tokens = len(doc_tokens)
    entities = {"entities": []}

    # Process text in chunks to handle large documents
    for start_idx in range(0, num_tokens, MAX_TOKEN_LENGTH):
        end_idx = min(start_idx + MAX_TOKEN_LENGTH, num_tokens)
        token_chunk = doc_tokens[start_idx:end_idx].text
        doc_chunk = nlp_model(token_chunk)

        # Extract entities from the chunk
        for ent in doc_chunk.ents:
            entities["entities"].append({
                "text": ent.text,
                "start_char": start_idx + ent.start_char,
                "end_char": start_idx + ent.end_char,
                "label": ent.label_
            })

    return entities


def update_database(cur, paper, entities):
    """
    Update the database with paper and entity information.

    :param cur: Database cursor for executing queries.
    :param paper: Dictionary containing paper metadata.
    :param entities: Dictionary containing extracted entities.
    """
    # Insert paper into database and retrieve paper_id
    paper_id = insert_paper(cur, paper)

    # Insert entities and relationships
    for entity in entities['entities']:
        entity_id = insert_entity(cur, entity)
        link_paper_entity(cur, paper_id, entity_id)


def insert_paper(cur, paper):
    """
    Insert paper_name, paper_pdf, paper_docx, paper_json, paper_entities from file_dict
    to table 'papers'

    :param cur: connection cursor
    :param file_dict: name, pdf, docx, json files and entities of a paper.
    :returns: paper_id
    """
    cur.execute("""
        INSERT INTO papers(paper_name, paper_pdf, paper_docx, paper_json, paper_entities)
        VALUES(:paper_name, :paper_pdf, :paper_docx, :paper_json, :paper_entities)
        ON CONFLICT(paper_name) DO UPDATE SET
            paper_pdf=:paper_pdf,
            paper_docx=:paper_docx,
            paper_json=:paper_json,
            paper_entities=:paper_entities
            RETURNING paper_id
    """, paper)
    return cur.fetchone()[0]


def insert_entity(cur, entity):
    """
    Insert entity_name, entity_type of each entity in entities into table 'entities'

    :param cur: connection cursor
    :param entity: information dictionary of entities detected in the text of the file
    :returns: entity_id
    """
    cur.execute("""
        INSERT INTO entities(entity_name, entity_type)
        VALUES(:entity_name, :entity_type)
        ON CONFLICT(entity_name, entity_type) DO UPDATE SET entity_name=:entity_name
            RETURNING entity_id
    """, {'entity_name': entity['text'], 'entity_type': entity['label']})
    return cur.fetchone()[0]


def link_paper_entity(cur, paper_id, entity_id):
    """
    Link a paper and an entity in the database by inserting entity_id of each entity in entities
    and paper_id into table 'papers_have_entities'

    :param cur: connection cursor
    :param paper_id: int, paper's ID
    :param entity_id: int, entity's ID
    """
    cur.execute("""
        INSERT INTO papers_have_entities(entity_id, paper_id)
        VALUES(:entity_id, :paper_id)
        ON CONFLICT(entity_id, paper_id) DO UPDATE SET count=count+1
    """, {'entity_id': entity_id, 'paper_id': paper_id})


def parse_user_query(user_input):
    """
    Construct a SQL query based on a natural language input.
    example: translate "get all papers that mention person Fiona Calvert" into SQL query
    "SELECT * FROM papers INNER JOIN papers_have_entities ON papers_have_entities.paper_id = papers.paper_id
    INNER JOIN entities ON papers_have_entities.entity_id = entities.entity_id WHERE entities.entity_type='PERSON'
    AND entities.name = 'Fiona Calvert' Limit 1"

    :param input_values: a string of query instructions in natural language
    :return: a constructed SQL query string that can be executed against a database
    """
    query_tokens = user_input.strip().split()
    query_parts = {
        "select": [],
        "from": [],
        "where": [],
        "limit": []
    }
    current_index = 0

    if query_tokens and query_tokens[current_index].lower() == 'get':
        current_index += 1

        # Handle 'one' or 'all'
        if current_index < len(query_tokens) and query_tokens[current_index].lower() == 'one':
            query_parts['limit'].append('LIMIT 1')
            current_index += 1
        elif current_index < len(query_tokens) and query_tokens[current_index].lower() == 'all':
            current_index += 1

        # Handle 'papers'
        if current_index < len(query_tokens) and query_tokens[current_index].lower() == 'papers':
            query_parts['select'].append('papers.*')
            query_parts['from'].append('papers')
            current_index += 1

        # Handle 'that mention ...'
        if current_index < len(query_tokens) and query_tokens[current_index].lower() == 'that':
            current_index += 1
            if current_index < len(query_tokens) and query_tokens[current_index].lower() == 'mention':
                current_index += 1
                query_parts['from'].append(
                    'INNER JOIN papers_have_entities ON papers_have_entities.paper_id = papers.paper_id')
                query_parts['from'].append('INNER JOIN entities ON papers_have_entities.entity_id = entities.entity_id')
                conditions = []

                while current_index < len(query_tokens):
                    current_index = parse_conditions(query_tokens, conditions, current_index)
                    if current_index < len(query_tokens):
                        logical_operator = query_tokens[current_index].lower()
                        if logical_operator in ('and', 'or'):
                            conditions.append(logical_operator.upper())
                            current_index += 1
                        else:
                            break

                if conditions:
                    query_parts['where'].append(' '.join(conditions))

    else:
        return ""

    query_string = f"SELECT {' '.join(query_parts['select'])} FROM {' '.join(query_parts['from'])}"
    if query_parts['where']:
        query_string += f" WHERE {' '.join(query_parts['where'])}"
    if query_parts['limit']:
        query_string += f" {' '.join(query_parts['limit'])}"

    return query_string


def parse_conditions(tokens, conditions, index):
    """
    Construct the condition clause of a SQL query by parsing user input.

    :param tokens: str, words in the natural language input
    :param conditions: accumulated query conditions
    :param index: current index of element in tokens to process

    :return: updated index after parsing conditions.
    """
    if index >= len(tokens):
        return index

    entity_type = None
    if tokens[index].lower() in ('person', 'organisation', 'work'):
        entity_type_map = {
            'person': 'PERSON',
            'organisation': 'ORG',
            'work': 'WORK_OF_ART'
        }
        entity_type = entity_type_map[tokens[index].lower()]
        index += 1

    # Collect entity name
    entity_name_tokens = []
    while index < len(tokens) and tokens[index].lower() not in ('and', 'or'):
        entity_name_tokens.append(tokens[index])
        index += 1

    entity_name = ' '.join(entity_name_tokens).replace("'", "''")  # Escape single quotes

    # Build condition
    condition = "("
    if entity_type:
        condition += f"entities.entity_type = '{entity_type}' AND "
    condition += f"entities.entity_name = '{entity_name}'"
    condition += ")"

    conditions.append(condition)
    return index


def run_cli_interface(conn):
    """
    Run the command-line interface for querying the database.

    :param conn: connection to SQLite database
    """
    cur = conn.cursor()
    question_completer = WordCompleter(
        ['get', 'one', 'all', 'papers', 'that', 'mention', 'person', 'organisation', 'work', 'and', 'or', 'q'],
        ignore_case=True
    )

    user_input = None
    while True:
        user_input = prompt(
            '>',
            history=FileHistory('history_psd.txt'),
            auto_suggest=AutoSuggestFromHistory(),
            completer=question_completer,
        )
        if user_input.lower() == 'q':
            break

        query_string = parse_user_query(user_input)
        if not query_string:
            print("Invalid query. Please try again.")
            continue

        cur.execute(query_string)
        results = cur.fetchall()
        if not results:
            print("No results found")
        else:
            for result in results:
                print(result)


def main():
    """
    Main function to orchestrate the document processing and CLI interface.
    """
    # Load spaCy model
    nlp_model = load_nlp_model()

    # Load paper index
    xlsx_path = Path(".", "index.xlsx")
    papers_to_process = load_paper_index(xlsx_path)

    # Setup database
    conn = get_database_connection(DB_FILE)
    setup_database(conn)

    # Process documents
    process_documents(papers_to_process, nlp_model, conn)

    # Run CLI interface
    run_cli_interface(conn)

    # Close database connection
    conn.close()


if __name__ == "__main__":
    main()
