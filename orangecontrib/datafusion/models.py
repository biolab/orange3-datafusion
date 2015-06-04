import functools
from copy import copy
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
        """ Column object type"""
        return self.relation.col_type

    @property
    def row_type(self):
        """Row object type"""
        return self.relation.row_type

    @property
    def name(self):
        """Relation name"""
        return self.relation.name

    @property
    @functools.lru_cache()
    def X(self):
        """
        :return: relation data
        """
        data = self.relation.data
        if np.ma.is_masked(data):
            mask = data.mask
            data = data.data.copy()
            data[mask] = np.nan
        else:
            data = data.copy()
        return data

    def __len__(self):
        """Number of rows in relation"""
        return len(self.relation.data)

    @classmethod
    def from_table(cls, domain, source, row_indices=...):
        return Table.from_table(domain, source, row_indices)


class RelationCompleter:
    @property
    def name(self):
        """"Completer name"""
        raise NotImplementedError()

    def retrain(self):
        """Retrain the completer using different random seed.

        Returns a new instance of the Completer.
        """
        raise NotImplementedError()

    def can_complete(self, relation):
        """Return True, if the completer had sufficient data to complete the
        given relation.
        """
        raise NotImplementedError()

    def complete(self, relation):
        """Return a completed relation.

         All masked values from the parameter relation should be replaced with the predicted ones.
         """
        raise NotImplementedError()


class FusionGraph:
    def __init__(self, fusion_graph):
        """Wrapper for skfusion FusionGraph

        :type fusion_graph: skfusion.fusion.FusionGraph
        """
        super().__init__()
        self._fusion_graph = fusion_graph

    @property
    def name(self):
        return getattr(self._fusion_graph, 'name', str(self))

    @property
    def n_object_types(self):
        return self._fusion_graph.n_object_types

    @property
    def n_relations(self):
        return self._fusion_graph.n_relations

    def draw_graphviz(self, *args, **kwargs):
        return self._fusion_graph.draw_graphviz(*args, **kwargs)

    def get_object_type(self, name):
        return self._fusion_graph.get_object_type(name)

    def get_names(self, object_type):
        return self._fusion_graph.get_names(object_type)

    def get_relations(self, object_type_1, object_type_2):
        return self._fusion_graph.get_relations(object_type_1, object_type_2)

    def out_relations(self, o1):
        return self._fusion_graph.out_relations(o1)


class FittedFusionGraph(FusionGraph, RelationCompleter):
    def __init__(self, fusion_fit):
        """Wrapper for skfusion Fusion Fit

        :type fusion_fit: skfusion.fusion.FusionFit
        """
        super().__init__(fusion_fit.fusion_graph)
        self._fusion_fit = fusion_fit

    @property
    def backbones_(self):
        return self._fusion_fit.backbones_

    @property
    def factors_(self):
        return self._fusion_fit.factors_

    def backbone(self, relation):
        return self._fusion_fit.backbone(relation)

    def factor(self, object_type):
        return self._fusion_fit.factor(object_type)

    # Relation Completer members
    def can_complete(self, relation):
        for fuser_relation in self.get_relations(relation.row_type,
                                                 relation.col_type):
            if fuser_relation._id == relation._id:
                return True

    def complete(self, relation):
        return self._fusion_fit.complete(relation)

    def retrain(self):
        fg = copy(self._fusion_fit)
        fg.fuse(self._fusion_graph)
        return FittedFusionGraph(fg)
