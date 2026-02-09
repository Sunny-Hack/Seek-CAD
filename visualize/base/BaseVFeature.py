from abc import ABC, abstractmethod


class BaseVFeature(ABC):
    def __init__(self, feat_name, feat_id, feat_type, parameters):
        self.feat_name = feat_name
        self.feat_id = feat_id
        self.feat_type = feat_type
        self.parameters = parameters

    @abstractmethod
    def back2json(self):
        pass

    @abstractmethod
    def to_deepcad_json(self):
        pass
