from . import settings
import mimetypes
import os
from urllib import parse

STATUSES = {
    10: "INPUT",
    11: "SENSITIVE INPUT",
    20: "SUCCESS",
    30: "REDIRECT - TEMPORARY",
    31: "REDIRECT - PERMANENT",
    40: "TEMPORARY FAILURE",
    41: "SERVER UNAVAILABLE",
    42: "CGI ERROR",
    43: "PROXY ERROR",
    44: "SLOW DOWN",
    50: "PERMANENT FAILURE",
    51: "NOT FOUND",
    52: "GONE",
    53: "PROXY REQUEST REFUSED",
    59: "BAD REQUEST",
    60: "CLIENT CERTIFICATE REQUIRED",
    61: "CERTIFICATE NOT AUTHORISED",
    62: "CERTIFICATE NOT VALID"
}

mimetypes.init()

for mime_type in settings['MIME_TYPES']:
    for extension in settings['MIME_TYPES'][mime_type]:
        mimetypes.add_type(mime_type, extension)


class GeminiResponse:

    def __init__(self, status, body=None, meta=None):
        self._status = status
        self._body = body
        self._meta = meta

    @property
    def status(self):
        return self._status

    @property
    def header(self):
        response_header = self._status
        if self._meta is not None:
            response_header = f"{self._status} {self._meta}"
        return f"{response_header}\r\n".encode('UTF-8')

    @property
    def body(self):
        return self._body        


class GeminiException(Exception):
    
    def __init__(self, code, meta=None):
        self.code = code
        self.meta = meta

    def __str__(self):
        return f"<GeminiException: {self.code} {STATUSES[self.code]}>"        

    def response(self):
        if self.meta is not None:
            response_meta = self.meta
        else:
            response_meta = STATUSES[self.code]
        return GeminiResponse(self.code, meta=response_meta)
        

class GeminiRequest:

    url = None
    host = None
    path = None
    is_index = False

    def __init__(self, *args):
        self.url = args[0]
        url_info = parse.urlparse(args[0])
        if url_info.scheme != 'gemini':
            raise GeminiException(59, f"Schéma d'URL `{url_info.scheme}` n'est pas supporté")
        self.host = url_info.netloc
        self.path = url_info.path

    @property
    def resource_path(self):
        return f"{settings['DOCUMENT_ROOT']}{self.path}"

    @property
    def resource_filename(self):
        return os.path.split(self.resource_path)[-1]

    @property
    def resource_mime_type(self):
        """
        Tente de déterminer le type MIME de  à patir de la ressource demandée
        """
        mime_type = mimetypes.guess_type(self.resource_filename)
        return mime_type[0]

    def _get_index(self, index_path):
        """
        Construit une liste de balises Gemini et établit des liens avec tous les fichiers du chemin d'accès donné.
        """
        files = os.listdir(index_path)  
        index = [f"# Index of {self.path}\r\n"]              
        for f in files:
            index.append(f"=> {self.path}{f} {f}")
        index = "\r\n".join(index) + "\r\n" 
        return index

    def _get_body(self, resource_path):
        """
        Chargement du contenu demandé ou listes de fichiers de construction
        """
        try:
            # Si le chemin des ressources est un fichier, charger son contenu et le retourner.
            with open(self.resource_path, 'rb') as f:
                data = f.read()
                return data, self.resource_mime_type
        except IsADirectoryError as e:
            # Si le résultat est un répertoire, vérifiez s'il y a un fichier d'index.
            index_path = f"{resource_path}{os.path.sep}{settings['INDEX_FILE']}"
            if os.path.exists(index_path):
                with open(index_path, 'rb') as f:                    
                    data = f.read()
                    return data, 'text/gemini'
            elif settings['AUTO_INDEX']:
            # S'il n'y a pas de fichier d'index et que AUTO_INDEX est activé, on obtient une liste de fichiers, on construit le balisage de l'index et on le renvoie.          
                index = self._get_index(resource_path)
                return index.encode("UTF-8"), 'text/gemini'
            else:
                # S'il n'y a pas de fichier d'index et que AUTO_INDEX n'est pas activé, lever une exception non trouvée.
                raise GeminiException(51, f"No index found")

    def dispatch(self):
        """
        Traite la demande. Tente de charger la ressource demandée et renvoie un objet GeminiResponse.
        """
        if not os.path.exists(self.resource_path):
            raise GeminiException(51, meta=f"`{self.path}` Not Found")
        
        data, mime_type = self._get_body(self.resource_path)
        
        return GeminiResponse(20, data, meta=mime_type)       
