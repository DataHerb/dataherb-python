from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel


class HerbTable:
    """Format search result

    A flora search result has the following structure:
    ```
    """

    def __init__(self, herb):
        self.herb = herb

    def panel(self):

        self.table()
        self.resource_tree()

    def table(self):
        """Summary Table"""
        table = Table(title=f"DataHerb: {self.herb.name}", show_lines=True)

        table.add_column("key", justify="right", style="cyan", no_wrap=False)
        table.add_column("value", style="magenta", no_wrap=False)

        table.add_row(f"ID", f"{self.herb.id}")
        table.add_row(f"Name", f"{self.herb.name}")
        table.add_row(f"Source", f"{self.herb.source}")
        table.add_row(f"Description", f"{self.herb.description}")
        table.add_row(f"URI", f"{self.herb.uri}")
        table.add_row(f"Metadata", f"{self.herb.metadata_uri}")

        pl = Panel(table, title=f"Summary of {self.herb.id}")

        return pl

    def resource_tree(self):
        """Show list of resources"""

        tree = Tree(f"{self.herb.id}")
        for r in self.herb.resources:
            tree.add(f'{r.descriptor.get("path")}')

        pl = Panel(tree, title=f"Resources of {self.herb.id}")

        return pl
