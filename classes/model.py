from classes.fields import Field, AutoField, ForeignKey
from classes.db import Connection
from classes.utils import DirtyFields, ToDataFrameList

class TableMeta(type):
    """
    Metaclasse reponsável por coletar todos os compos (`Field`), definidos nas subclasses de `Table`.
    """
    def __new__(mcls, name, bases, attrs):
        fields = {}
        for base in bases:
            if hasattr(base, '_fields'):
                fields.update(base._fields)

        for key, value in list(attrs.items()):
            if isinstance(value, Field):
                fields[key] = value
        attrs['_fields'] = fields
        return super().__new__(mcls, name, bases, attrs)

class Table(metaclass=TableMeta):
    """
    Class base para todas as tabelas do mini ORM.
    Responsável por instanciar objetos com base nos campos definidos.
    """
    _tables = []
    _saved = False
    _updated = False
    _deleted = False
    _dirty_fields = DirtyFields()
    id = AutoField()
    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)

        for key, field in cls._fields.items():
            value = kwargs.get(key, field.default)
            value = field.validate(value)
            setattr(instance, key, value)

        return instance

    def __init_subclass__(cls, **kwargs):
        """
        Executa quando uma nova subclasse é criada.
        Registra a tabela e seus campos.
        """
        super().__init_subclass__(**kwargs)
        if Table in cls.__bases__:
            Table._tables.append(cls)

    def __setattr__(self, name, value):
        if name == "id" and self._saved:
            raise AttributeError("The IDs of objects saved in the database cannot be changed")
        
        if name == "_saved" or name == "_dirty_fields" or name == "_updated" or name == "_deleted":
            raise AttributeError(f"The {name} attribute cannot be changed directly.")
        
        field = getattr(self.__class__, name, None)
        if isinstance(field, Field):
            value = field.validate(value)
            if self._deleted:
                raise AttributeError("Deleted objects cannot be changed.")
            
            if self._saved:
                if self.__dict__[name] != value:
                    copy = self._dirty_fields.copy()
                    copy.update({name: value})
                    object.__setattr__(self, "_dirty_fields", DirtyFields(copy))
                    object.__setattr__(self, "_updated", True)

        super().__setattr__(name, value)

    @property
    def to_dict(self):
        to_dict = {}
        for attr, field in self.__class__._fields.items():
            value = self.__dict__[attr]
            to_dict[attr] = value  if not field.__class__.__name__.lower() == "foreignkey" else value.to_dict

        return to_dict

    @classmethod
    def get_fields_meta(cls):
        meta = {}
        for name, field in cls._fields.items():
            meta[name] = field.get_metadata()
        return meta
    
    @classmethod
    def create_table(cls, if_not_exists=True):
        """
        Gera a string SQL para criar a tabela baseada em cls._fields / cls.get_fields_meta().
        Não executa nada - só retorna a query. 
        """
        table_name = cls.__name__.lower()
        fields_meta = cls.get_fields_meta()
        lines = []

        for col_name, metas in fields_meta.items():
            if not metas:
                raise ValueError(f"Field '{col_name}' não possui metadados")
            
            col_type = metas[0]
            constraints = metas[1:]
            col_parts = [f"`{col_name}`", col_type] + constraints
            col_sql = " ".join(part for part in col_parts if part)
            lines.append(col_sql)

        if_clause = "IF NOT EXISTS" if if_not_exists else ""
        sql = f"CREATE TABLE {if_clause} `{table_name}` (\n " + ",\n ".join(lines) + "\n);"
        return sql

    @classmethod
    def create_all_tables(cls):
        """
        Cria todas as tabelas registradas no banco
        """
        with Connection() as cursor:
            for table in cls._tables:
                sql = table.create_table()
                print(f"Criando a tablea: {table.__name__}")
                cursor.execute(sql)
        print("Todas as tabelas fora, criadas com sucesso!")

    def insert(self):
        """
        Insere dados a table 
        """
        if self._deleted:
            raise ValueError("Deleted objects cannot be saved")

        table_name = self.__class__.__name__.lower()
        fields = self._fields
        columns = []
        values = []

        for name, field in fields.items():
            value = getattr(self, name)
            if getattr(field, "auto_increment", False) and value is None:
                continue

            if getattr(field, "auto_increment", False) and value is not None:
                with Connection() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {name} = ?", (value,))
                    if cursor.fetchone()[0] > 0:
                        raise ValueError(f"ID {value} alredy exists in table '{table_name}")
                    
            columns.append(name)
            values.append(value)

        placeholders = ", ".join(["?"] * len(values))
        columns_sql = ", ".join(columns)
        sql = f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders})"
        with Connection() as cursor:
            cursor.execute(sql, values)
            if any(getattr(f, "auto_increment", False) for f in fields.values()):
                object.__setattr__(self, "id", cursor.lastrowid)
        object.__setattr__(self, "_saved", True)

    @classmethod
    def select(cls, where=None, limit=None, **kwargs):
        """
        Lê os dados da table, sem argumnetos retonar todos os dados, com limit default None.
        Args:
            where or **kwargs (dict): Gera o filtro da table (and), com limit default 1 quando um filtro é definido.
            limit (int | None): defini a quantidade limite de dados a ser retonando.
        """
        table_name = cls.__name__.lower()
        filters = {}
        conditions = ""

        if where:
            filters.update(where)
        if kwargs:
            filters.update(kwargs)

        if filters:
            where = []
            # Valida se todos os filtros são correspondente aos compos da tabela.
            valid_fields = cls._fields.keys()
            for key in filters.keys():
                if key not in valid_fields:
                    raise ValueError(f"The '{key}' field does not exist in '{cls.__name__}'")    
                where.append(f"{key} = ?")
            conditions += " WHERE " + " AND ".join(where)

        if filters and limit is None:
            limit = 1
        
        query = f"SELECT * FROM {table_name}" + conditions

        if limit is not None:
            query += f" LIMIT {limit}"

        params = tuple(filters.values())

        with Connection() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]
        result = []
        for row in rows:
            data = dict(zip(columns, row))
            pk = data.pop("id", None)
            obj = cls(**data)
            object.__setattr__(obj, "id", pk)
            object.__setattr__(obj, "_saved", True)
            # Lidando com os compos que são ForeignKey, e preenchendo-os com seus repectivos models.
            for key, value in data.items():
                foreignkey = cls._fields[key]
                if foreignkey.__class__.__name__.lower() == "foreignkey":
                    foreignkey_instance = foreignkey.to.select(id=value)
                    object.__setattr__(foreignkey_instance, "_saved", True)
                    object.__setattr__(obj, key, foreignkey_instance)

            result.append(obj)

        if limit == 1:
            return result[0] if result else None
        return ToDataFrameList(result)

    def update(self):
        """
        Atualiza os compos infomados no banco de dados e no proprio objeto.
        Return (boolen): True se bem sucedido e False se não.
        """
        if not self._saved:
            raise AttributeError(f"It is only possible to update data saved in the database.")

        if not self._updated: return False
        
        updates = {}
        for field, value in self._dirty_fields.copy().items():
            # verifcando se é uma foreignKei e convertendo pra int.
            field_type = getattr(self.__class__, field, None)
            if isinstance(field_type, ForeignKey):
                if isinstance(value, field_type.to):
                    # ID da instância relacionada.
                    value = value.id 
                elif not isinstance(value, (int, type(None))):
                    raise TypeError(f"The {field} field must receive an id or instance of {field_type.to.__class__.__name__}")
                
            updates[field] = value

        # Gerar SQL do update
        set_clause = ", ".join(f"{f} = ?" for f in updates.keys())
        params = list(updates.values()) + [self.id]
        query = f"UPDATE {self.__class__.__name__.lower()} SET {set_clause} WHERE id = ?"
        print(query, params)
        with Connection() as cursor:
            cursor.execute(query, params)

        for field, value in updates.items():
            object.__setattr__(self, field, value)

        object.__setattr__(self, "_updated", False)
        object.__setattr__(self, "_dirty_fields", DirtyFields({}))

        return True

    def delete(self):
        """
        Deleta um objeto salvo no banco de dados.
        return (boolean)
        """
        if not self._saved:
            raise ValueError("It is permitted to delete data saved in te database")
        
        table_name = self.__class__.__name__.lower()
        query = f"DELETE FROM {table_name} WHERE id = ?"

        with Connection() as cursor:
            cursor.execute(query, [self.id])

        object.__setattr__(self, "_saved", False)
        object.__setattr__(self, "_deleted", True)
        return True