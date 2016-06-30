# Graphviz

Install dependencies required to make django-extensions "model graph" work with the following:

sudo apt-get install -y graphviz libgraphviz-dev pkg-config
pip install pygraphviz

From the docs

    # Create a dot file
    $ ./manage.py graph_models -a > my_project.dot
    # Create a PNG image file called my_project_visualized.png with application grouping
    $ ./manage.py graph_models -a -g -o my_project_visualized.png

    # Same example but with explicit selection of pygraphviz or pydot
    $ ./manage.py graph_models --pygraphviz -a -g -o my_project_visualized.png
    $ ./manage.py graph_models --pydot -a -g -o my_project_visualized.png
    # Create a dot file for only the 'foo' and 'bar' applications of your project
    $ ./manage.py graph_models foo bar > my_project.dot
