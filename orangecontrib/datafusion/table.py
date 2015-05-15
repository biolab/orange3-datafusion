from Orange.data import Table, Domain, ContinuousVariable, StringVariable

import numpy as np


class Relation(Table):
    """Wrapper for `skfusion.fusion.Relation`
    """
    def __new__(cls, *args, **kwargs):
        """Bypass Table.__new__."""
        return object.__new__(Relation)

    def __init__(self, relation):
        """Create a wraper for fusion.Relation.

        Parameters:
        -----------
        relation: An instance of `skfusion.fusion.Relation`
        """
        self.relation = relation

        empty = self._Y = self.W = np.zeros((len(relation.data), 0))
        if relation.row_names is not None:
            self.metas = np.array([str(x) for x in relation.row_names],
                                  dtype='object')[:, None]
            metas_vars = [StringVariable(str(relation.row_type))]
        else:
            self.metas = empty
            metas_vars = []

        if relation.col_names is not None:
            var_names = relation.col_names
        else:
            var_names = range(relation.data.shape[1])
        self.domain = Domain([ContinuousVariable(name)
                              for name in map(str, var_names)],
                             metas=metas_vars)
        Table._init_ids(self)

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
