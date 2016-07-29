import os
import json

from bs4 import BeautifulSoup
import petl

PYTHON_DOC_BASE_URL = 'https://docs.python.org/3.5{}'
DOWNLOADED_HTML_PATHS = {'python3': 'download/python-3.5.2-docs-html',
                         'python2': 'download/python-2.7.12-docs-html'}


class PythonData(object):
    """
    Object responsible for loading raw HTML data from Python docs:
    """
    def __init__(self, file):
        """
        Initialize PythonData object. Load data from HTML.

        """
        self.HTML = ""
        self.FILE = file
        self.load_data()

    def load_data(self):
        """
        Open the HTML file and load it into the object.

        """
        with open(self.FILE, 'r') as data_file:
            self.HTML = data_file.read()

    def get_raw_data(self):
        """
        Returns: The raw HTML that was loaded.

        """
        return self.HTML

    def get_file(self):
        """
        Returns: The file path of the file being used.

        """
        return self.FILE


class PythonDataParser(object):
    """
    Object responsible for parsing the raw HTML that contains Python data
    """
    def __init__(self, data_object, download_path):
        """
        Given raw data, get the relevant sections
        Args:
            raw_data: HTML data
            path: path of downloaded HTML data
        """
        self.parsed_data = None
        self.function_sections = []
        self.method_sections = []
        self.intro_text = ''
        self.title = ''
        self.download_path = download_path

        self.file_being_used = data_object.get_file()

        soup_data = BeautifulSoup(data_object.get_raw_data(), 'html.parser')
        sections = soup_data.find_all('div', {'class': 'section'})

        for section in sections:
            functions = section.find_all('dl', {'class': 'function'})
            if functions:
                self.function_sections.extend(functions)

            methods = section.find_all('dl', {'class': 'method'})
            if methods:
                self.method_sections.extend(methods)

        intro = soup_data.find_all('p', limit=2)
        for p in intro:
            self.intro_text += p.text.replace('  ', ' ').replace('\n', ' ').replace('\\n', r'\\n')

        title = soup_data.find('a', {'class': 'reference internal'})
        if title:
            self.title = title.text

    def parse_for_module_name(self, section):
        """
        Returns the module name
        Args:
            section: A section of parsed HTML that represents a function definition

        Returns:
            Name of the module

        """
        module_name = section.find('code', {'class': 'descclassname'})
        if module_name:
            return module_name.text.rstrip('.')
        return ''


    def parse_for_function_name(self, section):
        """
        Returns the function name
        Args:
            section: A section of parsed HTML that represents a function definition

        Returns:
            Name of function

        """
        function_name = section.find('code', {'class': 'descname'})
        if function_name:
            return function_name.text
        return ''

    def parse_for_first_paragraph(self, section):
        """
        Returns the first paragraph of text for a given function
        Fixes up some weird double spacing and newlines.
        Args:
            section: A section of parsed HTML that represents a function definition

        Returns:
            First paragraph found with text

        """
        paragraphs = section.find_all('p')
        for paragraph in paragraphs:
            if paragraph.text:
                return paragraph.text.replace('  ', ' ').replace('\n', ' ').replace('\\n', r'\\n')
        return ''

    def parse_for_anchor(self, section):
        """
        Returns the anchor link to specific function doc
        Args:
            section: A section of parsed HTML that represents a function definition

        Returns:
            The href value of the link to doc

        """
        a_tag = section.find('a', {'class': 'headerlink'})
        if a_tag:
            return a_tag['href']
        return ''

    def parse_for_method_signature(self, section):
        """
        Returns the method signature
        Args:
            section: A section of parsed HTML that represents a function definition

        Returns:
            The method signature

        """
        dt = section.find('dt')
        if dt:
            return '<pre><code>{}</code></pre>'.format(dt.text.replace('¶', '').replace('\n', '').replace('\\n', r'\\n'))
        return ''

    def parse_for_class_method(self, section):
        """
        Returns the class.module.method signature
        Args:
            section: A section of parsed HTML that represents a method definition

        Returns:
            The method signature

        """
        id_tag = section.find('dt').get('id')
        if id_tag:
            tag_parts = id_tag.split('.')

            # if it doesnt fit the pattern
            #  module.class.method
            # then concat the remaining parts into the method name
            # ex: email.message.EmailMessage.is_attachment
            if len(tag_parts) == 3:
                return tag_parts
            elif len(tag_parts) > 3:
                return tag_parts[0], tag_parts[1], '.'.join(tag_parts[2:])
        return ['','','']

    def create_url(self, anchor):
        """
        Helper method to create URL back to document
        Args:
            anchor: #anchor

        Returns:
            Full URL to function on the python doc

        """
        file_path = self.file_being_used.replace(self.download_path, '')
        return PYTHON_DOC_BASE_URL.format('{}{}'.format(file_path, anchor))

    def parse_for_data(self):
        """
        Main gateway into parsing the data. Will retrieve all necessary data elements.
        """
        data = []

        if self.intro_text and self.title:
            data_elements = {
                'module': self.title,
                'function': '',
                'method_signature': '',
                'first_paragraph': self.intro_text,
                'url': self.create_url('')
            }
            data.append(data_elements)

        for function_section in self.function_sections:
            module = self.parse_for_module_name(function_section)
            function = self.parse_for_function_name(function_section)
            if module or function:
                method_signature = self.parse_for_method_signature(function_section)
                first_paragraph = self.parse_for_first_paragraph(function_section)
                anchor = self.parse_for_anchor(function_section)
                url = self.create_url(anchor)

                data_elements = {
                    'module': module,
                    'function': function,
                    'method_signature': method_signature,
                    'first_paragraph': first_paragraph,
                    'url': url,
                }

                data.append(data_elements)
        
        for method_section in self.method_sections:
            module, class_name, method = self.parse_for_class_method(method_section)
            if method:
                method_signature = self.parse_for_method_signature(method_section)
                first_paragraph = self.parse_for_first_paragraph(method_section)
                url = self.create_url("#" + '.'.join([module,class_name,method]))

                data_elements = {
                    'module': module,
                    'function':  class_name + "." + method,
                    'method_signature': method_signature,
                    'first_paragraph': first_paragraph,
                    'url': url,
                }

                data.append(data_elements)

        self.parsed_data = data

    def get_data(self):
        """
        Get the parsed data.
        Returns:
            self.parsed_data: Dict containing necessary data elements
        """
        return self.parsed_data


class PythonDataOutput(object):
    """
    Object responsible for outputting data into the output.txt file
    """
    def __init__(self, data, version):
        self.data = data
        if version == 'python2':
            self.output = 'output_py2.txt'
        else:
            self.output = 'output.txt'

    def create_names_from_data(self, data_element):
        """
        Figure out the name of the function. Will contain the module name if one exists.
        Args:
            data_element: Incoming data dict

        Returns:
            Name, with whitespace stripped out

        """
        module = data_element.get('module')
        function = data_element.get('function')

        dotted_name = '{}{}{}'.format(module, '.' if module and function  else '', function)
        spaced_name = '{} {}'.format(module, function)

        return dotted_name.strip(), spaced_name.strip()

    def create_file(self):
        """
        Iterate through the data and create the needed output.txt file, appending to file as necessary.

        """
        with open(self.output, 'a') as output_file:
            for data_element in self.data:
                if data_element.get('module') or data_element.get('function'):
                    method_signature = data_element.get('method_signature')
                    first_paragraph = data_element.get('first_paragraph')
                    name, redirect = self.create_names_from_data(data_element)

                    abstract = '{}{}{}'.format(method_signature, '<br>' if method_signature and first_paragraph else '', first_paragraph)
                    url = data_element.get('url')
                    list_of_data = [
                        name,                       # unique name
                        'A',                        # type is article
                        '',                         # no redirect data
                        '',                         # ignore
                        '',                         # no categories
                        '',                         # ignore
                        '',                         # no related topics
                        '',                         # ignore
                        'https://docs.python.org',  # add an external link back to Python home
                        '',                         # no disambiguation
                        '',                         # images
                        abstract,                   # abstract
                        url                         # url to doc
                    ]
                    output_file.write('{}\n'.format('\t'.join(list_of_data)))

                    # Add redirect if we got a redirect name that is different from the original name
                    if redirect != name:
                        list_of_data = [
                            redirect,                   # unique name
                            'R',                        # type is redirect
                            name,                       # redirect alias, to the original data
                            '',                         # ignore
                            '',                         # no categories
                            '',                         # ignore
                            '',                         # no related topics
                            '',                         # ignore
                            '',                         # no external link
                            '',                         # no disambiguation
                            '',                         # images
                            '',                         # no abstract
                            ''                          # no url
                        ]
                        output_file.write('{}\n'.format('\t'.join(list_of_data)))


def unify():
    """
    Compare python3 and python2 abstracts by key keeping python2 entry only if the abstracts differ.

    """
    header = ['name', 'article_type', 'redirects', 'ignore', 'categories', 'ignore2', 'related', 'ignore3', 'external_links', 'disambiguation', 'images', 'abstract', 'url']
    table2 = (petl
                 .fromtsv('output_py2.txt')
                 .setheader(header)
                 .sort(key='name')
                 .unique(key='name')
                 .lookup('name')
             )

    table3 = (petl
                 .fromtsv('output.txt')
                 .setheader(header)
                 .sort(key='name')
                 .unique(key='name')
                 .lookup('name')
             )

    new_table2 = []
    differ = 0
    nf = 0
    for k, v in table3.items():
        if k in table2 and v[0][11] != table2[k][0][11]:
            differ += 1
            new_table2.append(v[0])
        else:
            nf += 1
    print('differ: %i\nnf:%i' % (differ, nf))
    with open('output_py2.txt', 'w') as out_file:
        for item in new_table2:
            out_file.write('{}\n'.format('\t'.join(i for i in item)))


def pre_parse():
    """
    Cleanup output.txt's files.  Mostly for use during local dev/testing.
    """
    if os.path.isfile('output.txt'):
        os.remove('output.txt')
    if os.path.isfile('output_py2.txt'):
        os.remove('output_py2.txt')

if __name__ == "__main__":
    pre_parse()
    for version, download_path in DOWNLOADED_HTML_PATHS.items():
        print('starting download_path: %s' % download_path)
        for dir_path, dir_name, file_names in os.walk(download_path):
            for file_name in file_names:
                if '.html' in file_name:
                    file_path = '/'.join((dir_path, file_name))
                    data = PythonData(file_path)
                    parser = PythonDataParser(data, download_path)
                    parser.parse_for_data()
                    output = PythonDataOutput(parser.get_data(), version)
                    output.create_file()
    unify()
