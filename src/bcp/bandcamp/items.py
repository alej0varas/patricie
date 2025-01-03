import types


class ItemBase:
    def __init__(self, url):
        self.url = url

    def update(self, content):
        for k, v in content.items():
            setattr(self, k, v)

    def to_dict(self):
        d = dict()
        for k, v in self.__dict__.items():
            if k.startswith("_"):
                continue

            if isinstance(v, types.MethodType):
                continue
            d[k] = v
        return d


class ItemWithChildren:
    def __init__(self):
        self.children = dict()

    def add_childrens(self, children_urls):
        for c_url in children_urls:
            self.add_children(self.children_class(c_url))

    def add_children(self, children):
        self.children[children.url] = children

    def get_children(self, children_url):
        return self.children.get(children_url)


class ItemWithParent:
    def __init__(self):
        self._parent_obj = None

    @property
    def parent(self):
        return self._parent_obj

    @parent.setter
    def parent(self, item):
        if item.of_type != self.parent_type:
            raise ValueError(f"parent type {item.of_type} is not {self.parent_type}")
        self._parent_obj = item
