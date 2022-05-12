from dataherb.utils.awscli import aws_cli as _aws_cli


def upload_dataset_to_s3(source: str, target: str) -> None:
    """
    upload_dataset_to_s3 uploads the dataset to S3

    :param source: local folder
    :param target: remote s3 uri
    """

    _aws_cli(("s3", "sync", source, target))
