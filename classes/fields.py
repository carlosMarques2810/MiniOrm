class Field:
    """
    Representa um campo (coluna) de uma tabela no mini ORM.

    Args:
        field_type (type): Tipo de dado esperado (ex: int, str, float, etc.).
        default (Any): Valor padrão caso nemhun seja fornecido.
        unique (bool): define se o campo deve ser unico.
        null (bool): Permite valor nulo no banco.
        blank (bool): Permite valor em branco (semelhante a null).
        primary_key (bool): Permite que o campo seja uma chave primária.
        auto_incremente (bool): Permite gerar um indice automático, principalmente qundo usado em conjunto com a primary_key.
        max_length (str | int): Em conjunto com o tipo 'str', no 'SQL' o metadado se tonar 'VARCHAR(max_lenght)', quando omitido, 'TEXT'.
    """
    def __init__(
            self, 
            field_type=None, 
            default=None, 
            unique=False, 
            null=False, 
            blank=False, 
            primary_key=False, 
            auto_increment=False, 
            max_length=None, 
        ):
        self.field_type = field_type
        # Valida o valor passado pra default com base no tipo esperado.
        self.default = (default and self.type_of(field_type, default)) or default
        self.unique = unique
        self.null = null
        self.blank = blank
        self.primary_key = primary_key
        self.auto_increment = auto_increment
        self.max_length = max_length

    def sql_type(self):
        """
        Retorna o tipo SQL equivalente ao tipo python.
        """
        if self.field_type is int:
            return "INT" if not self.primary_key else "INTEGER"
        
        elif self.field_type is str:
            if self.max_length:
                return f"VARCHAR({self.max_length})"
            return "TEXT"
        
        elif self.field_type is float:
            return "FLOAT"
        
        elif self.field_type is bool:
            return "BOOLEAN"
        
        else:
            raise TypeError(f"Unsupported type: {self.field_type}")

    def type_of(self, field_type, value):
        if not field_type:
            raise TypeError("Provide a type for validattion.")
        
        if not isinstance(value, field_type):
            raise ValueError(f"Expected {field_type}, got {type(value)}")
        return value
    
    def sql_constraints(self):
        """
        Retorna as retrições SQL do campo.
        """

        constraints = []
        if self.primary_key:
            constraints.append("PRIMARY KEY")
            self.null = True if not self.null else False
        if not self.null:                                                                                                                                                                                                                                                                                                                                                                                                                         
            constraints.append("NOT NULL")
        if self.blank:
            constraints.append("BLANK")
        if self.unique:
            constraints.append("UNIQUE")
        if self.auto_increment:
            constraints.append("AUTOINCREMENT")
        if self.default is not None:
            constraints.append(f"DEFAULT {self.default if isinstance(self.default, str) else str(self.default)}")
        return constraints
    
    def get_metadata(self):
        """
        Retorna uma lista de metadados SQL, ex: ["INT", "NOT NULL", "UNIQUE"]
        """
        return [self.sql_type()] + self.sql_constraints()
    
    def validate(self, value=None):
        if value is None and not self.default and not (self.null or self.blank):
            raise ValueError("A value is required for this field.")
        
        if value is None and not self.default and (self.null or self.blank):
            return None

        if value is None and self.default:
            return self.default
        
        return self.type_of(self.field_type, value)

class AutoField(Field):
    def __init__(self, allow_manual=False):
        super().__init__(int, primary_key=True, auto_increment=True)
        self.allow_manual = allow_manual

    def validate(self, value=None):
        if value is not None and not isinstance(value, int):
            raise TypeError(f"AutoField must be int, got {type(value).__name__}.")

        if value is not None and not self.allow_manual:
            raise ValueError("Manual assingnment of AutoField is not allowed.")
        
        return value
    
    def get_metadata(self):
        return ["INTEGER", "PRIMARY KEY", "AUTOINCREMENT"]

class ForeignKey(Field):
    """
    to (Table): Class da tabela referênciada (ex: User, Product, etc.)
    **kwargs (dict): Argumentos adicionais herdados de Field (null, default, unique...)  
    """
    def __init__(self, to, **kwargs):
        super().__init__(int, **kwargs)
        self.to = to

    def get_metadata(self):
        meta = [self.sql_type()]
        if not self.null:
            meta.append("NOT NULL")

        table_name = self.to.__name__.lower()
        meta.append(f"REFERENCES {table_name}(id)")
        
        return meta
    
    def validate(self, value):
        """
        Valida e retorna o ID da instância relacionada.
        """
        if isinstance(value, self.to):
            fk_value = getattr(value, "id", None)
            if fk_value is None:
                raise ValueError(f"The instance of {self.t.__name__} has no 'id' attribute defined.")
            return fk_value

        if isinstance(value, int):
            if value <= 0:
                raise ValueError(f"ForeignKey ID must be a positive integer, got {value}.")
            return value

        raise TypeError(f"ForeignKey expects an instance of {self.to.__name__} or int, got {type(value).__name__}.")