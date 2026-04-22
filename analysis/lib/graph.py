import pandas as pd
import numpy as np


class DirectedGraph(object):
    def __init__(self, df, source, target):
        """Create DirectedGraph from data frame with source and target columns.

        Parameters
        ----------
        df : DataFrame,
        source : str
            name of source column
        target : str
            name of target_column
        """

        # save only unique combinations of source => target
        df = df.drop_duplicates(subset=[source, target])

        self.adj_matrix = df.set_index(target).groupby(source).groups
        self._size = len(self.adj_matrix)

    def __len__(self):
        return self._size

    @classmethod
    def from_arrays(cls, source, target):
        """Create DirectedGraph from arrays of sources and arrays of targets.

        Arrays must be the same length.

        Parameters
        ----------
        source : ndarray
        target : ndarray

        Returns
        -------
        DirectedGraph
        """

        return cls(
            pd.DataFrame({"source": source, "target": target}),
            source="source",
            target="target",
        )

    def components(self):
        """Find all connected components in graph.

        Adapted from networkx::connected_component

        Returns
        -------
        list of sets
            each set is the connected nodes in the graph
        """
        groups = []
        seen = set()
        for node in self.adj_matrix.keys():
            if node not in seen:
                # add current node with all descendants
                adj_nodes = {node} | self.descendants(node)
                seen.update(adj_nodes)
                groups.append(adj_nodes)

        return groups

    def descendants(self, sources):
        """Find all descendants of sources as a 1d array (one entry per node in
        sources) using a breadth-first search.

        Parameters
        ----------
        nodes : list-like or singular node
            1d ndarray if sources is list-like, else singular list of nodes
        """

        def _descendants(node):
            """Traverse adjacency matrix using breadth-first search to find all
            connected notes for a given starting node.

            Parameters
            ----------
            node : number or string
                Starting node from which to find all adjacent nodes

            Returns
            -------
            set of adjacent nodes
            """
            out = set()
            next_nodes = set(self.adj_matrix.get(node, []))
            while next_nodes:
                nodes = next_nodes
                next_nodes = set()
                for next_node in nodes:
                    if next_node not in out:
                        out.add(next_node)
                        next_nodes.update(self.adj_matrix.get(next_node, []))
            return out

        f = np.frompyfunc(_descendants, 1, 1)
        return f(sources)
