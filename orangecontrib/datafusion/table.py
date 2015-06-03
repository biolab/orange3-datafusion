from Orange.data import Table, Domain, ContinuousVariable, StringVariable, Variable

import numpy as np


class Relation(Table):
    """Wrapper for `skfusion.fusion.Relation`
    """
    def __new__(cls, *args, **kwargs):
        """Bypass Table.__new__."""
        return object.__new__(Relation)

    def __init__(self, relation):
        """Create a wrapper for fusion.Relation.

        Parameters:
        -----------
        relation: An instance of `skfusion.fusion.Relation`
        """
        self.relation = relation
        meta_vars, self.metas = self._create_metas(relation)
        self._Y = self.W = np.zeros((len(relation.data), 0))

        if relation.col_names is not None:
            attr_names = relation.col_names
        else:
            attr_names = range(relation.data.shape[1])
        self.domain = Domain([ContinuousVariable(name)
                              for name in map(str, attr_names)],
                             metas=meta_vars)
        Table._init_ids(self)

    @staticmethod
    def _create_metas(relation):
        metas = []
        metas_data = [[] for x in relation.data]
        if relation.row_metadata is not None:
            metadata_names = set()
            for md in relation.row_metadata:
                metadata_names.update(md.keys())
            metadata_names = sorted(metadata_names, key=str)

            metas.extend(metadata_names)
            for md, v in zip(metas_data, relation.row_metadata):
                for k in metadata_names:
                    md.append(v.get(k, np.nan))
        elif relation.row_names is not None:
            metas = [relation.row_type.name]
            metas_data = [[name] for name in relation.row_names]

        def create_var(x):
            if isinstance(x, Variable):
                return x
            else:
                return StringVariable(str(x))

        metas_vars = [create_var(x) for x in metas]
        metas = np.array(metas_data, dtype='object')
        return metas_vars, metas

    @property
    def col_type(self):
        return self.relation.col_type

    @property
    def row_type(self):
        return self.relation.row_type

    @property
    def name(self):
        """
        :return: name of the relation
        """
        return self.relation.name

    @property
    def X(self):
        """
        :return: relation data
        """
        return self.relation.data

    def __len__(self):
        """
        :return: number of rows in relation
        """
        return len(self.relation.data)

    @classmethod
    def from_table(cls, domain, source, row_indices=...):
        return Table.from_table(domain, source, row_indices)
