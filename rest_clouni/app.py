from flask import Flask, send_file, request
import logging
from marshmallow import Schema, fields, validate
from marshmallow.exceptions import ValidationError
from toscatranslator.common.translator_to_configuration_dsl import translate
import os
import json

app = Flask(__name__)

PROVIDERS_DIR = './toscatranslator/providers/'
PROVIDERS_SUPPORTED = [
    x[0].replace(PROVIDERS_DIR, '')
    for x in os.walk(PROVIDERS_DIR)
    if '__pycache__' not in x[0] and x[0] != PROVIDERS_DIR
]
CONFIGURATION_TOOLS_SUPPORTED = ['ansible']

logging.info(f"API is mind to support providers: {PROVIDERS_SUPPORTED}")


class ToscaTemplate(Schema):
    template_file = fields.String(required=True)
    validate_only = fields.Boolean(default=False)
    provider = fields.String(required=True, validate=validate.OneOf(PROVIDERS_SUPPORTED))
    configuration_tool = fields.String(required=True, validate=validate.OneOf(CONFIGURATION_TOOLS_SUPPORTED))
    cluster_name = fields.String(required=True)
    is_delete = fields.Boolean(default=False)

    extra = fields.Method("get_extra", default={}, deserialize="load_extra")

    log_level = fields.String(default='info', validate=validate.OneOf([
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
        logging.ERROR,
        logging.ERROR
    ]))
    host_ip_parameter = fields.String(default='public_address',
                                      validate=validate.OneOf(['public_address', 'private_address']))
    debug = fields.Boolean(default=False)

    def get_extra(self, obj):
        return {'global': obj.get('extra', {})}

    def load_extra(self, value):
        return json.loads(value)


template_schema = ToscaTemplate()


@app.route("/favicon.ico")
def favicon():
    return send_file("./static/favicon-96x96.png")


@app.route("/", methods=['POST'])
def clouni_json():
    try:
        content = template_schema.load(request.json)
        parser_args = template_schema.dump(content)
        output = translate(**parser_args, a_file=False)
        if parser_args['debug']:
            result = {}
            for path in os.listdir('./artifacts'):
                with open('./artifacts/' + path, 'r') as f:
                    result[path] = f.read()
            result['playbook.yml'] = output
            return json.dumps(result)
        else:
            return json.dumps(output)

    except ValidationError as ve:
        return ve.messages