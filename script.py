import requests

url = 'http://127.0.0.1:5000/graphql'

def execute_query(query):
    response = requests.post(url, json={'query': query})
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Query failed: {response.text}')

def create_book(title, author, published_date, isbn, num_pages, cover_image_url):
    mutation = f'''
    mutation {{
      createBook(
        title: "{title}",
        author: "{author}",
        publishedDate: "{published_date}",
        isbn: "{isbn}",
        numPages: {num_pages},
        coverImageUrl: "{cover_image_url}"
      ) {{
        book {{
          id
          title
          author
          publishedDate
          isbn
          numPages
          coverImageUrl
        }}
      }}
    }}
    '''
    result = execute_query(mutation)
    print('New book added:')
    print(result)

def fetch_books():
    query = '''
    query {
      books {
        id
        title
        author
        publishedDate
        isbn
        numPages
        coverImageUrl
      }
    }
    '''
    result = execute_query(query)
    print('List of all books:')
    print(result)

def update_book(id, title=None, author=None, published_date=None, isbn=None, num_pages=None, cover_image_url=None):
    mutation = f'''
    mutation {{
      updateBook(
        id: "{id}",
        title: "{title}",
        author: "{author}",
        publishedDate: "{published_date}",
        isbn: "{isbn}",
        numPages: {num_pages},
        coverImageUrl: "{cover_image_url}"
      ) {{
        book {{
          id
          title
          author
          publishedDate
          isbn
          numPages
          coverImageUrl
        }}
      }}
    }}
    '''
    result = execute_query(mutation)
    print('Updated book details:')
    print(result)

def delete_book(id):
    mutation = f'''
    mutation {{
      deleteBook(id: {id}) {{
        book {{
          id
        }}
      }}
    }}
    '''
    result = execute_query(mutation)
    print('Book deleted:')
    print(result)

if __name__ == '__main__':
    # Add a new book
    # create_book('Python Crash Course', 'Eric Matthes', '2015-11-01', '978-1-59327-603-4', 560, 'https://en.wikipedia.org/wiki/Python_(programming_language)#/media/File:Python-logo-notext.svg'),
    # create_book('C++ Primer', 'Stanley B. Lippman, Josée Lajoie, Barbara E. Moo', '2012-08-06', '978-0321714114', '976', 'https://en.wikipedia.org/wiki/C%2B%2B#/media/File:ISO_C++_Logo.svg')

    #fetch data
    fetch_books()

    #update book
    #  update_book('17','CSS: The Definitive Guide', 'Eric A. Meyer', '2017-11-07', '978-1449393199', 1090, 'https://en.wikipedia.org/wiki/CSS#/media/File:CSS3_logo_and_wordmark.svg')

    # Delete a book 
    #  delete_book('16')



