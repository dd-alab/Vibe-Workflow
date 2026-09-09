class ServiceValidationError(Exception):
    pass


class UnsupportedMediaTypeError(Exception):
    pass


class UploadTooLargeError(Exception):
    pass


class AssetFileMissingError(Exception):
    def __init__(self, asset_id, variant: str) -> None:
        self.asset_id = asset_id
        self.variant = variant
        super().__init__("Le fichier local de cet asset est manquant.")
