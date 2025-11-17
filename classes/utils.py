class DirtyFields(dict):
    """
    Armazena e controla atributos modificados ("dirty fields") de um objeto, usada internamente para rastrear compos modificados para o UPDATE.
    Ela registra os campos que foram alterados em um modelo e impede que valores sejam sobrescritos diretamente.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def __setitem__(self, key, value):
        raise AttributeError("This dict cannot be set directly")
    

class ToDataFrameList(list):
    """
    Extenssão de list que exibe seus elementos como um Dataframe do Pandas.
    Ideal para representar coleçoes de objetos de modelos. Permitindo uma visualização dos dados no terminal, semelhante ao pandas
    """
    def __init__(self, iterable=None):
        iterable = iterable or []
        super().__init__(iterable)

    def __str__(self):
        import pandas as pd
        rows = [obj.to_dict for obj in self]
        df = pd.DataFrame(rows)
        return df.__str__() if not df.empty else "<empty QuerySet>"