from datetime import datetime
from http.client import BAD_REQUEST, NOT_FOUND, INTERNAL_SERVER_ERROR, UNAUTHORIZED, NO_CONTENT

from flask import Blueprint, abort, request, Response

from core.app_manager import manager
from core.exceptions import WireguardError
from web.controllers.RestController import RestController
from web.controllers.ViewController import ViewController
from web.static.assets.resources import EMPTY_FIELD, APP_NAME
from web.utils import get_all_interfaces, get_routing_table, get_wg_interfaces_summary, get_wg_interface_status


class Router(Blueprint):

    def __init__(self, name, import_name):
        super().__init__(name, import_name)


router = Router("router", __name__)


@router.route("/")
@router.route("/dashboard")
def index():
    context = {
        "title": "Dashboard"
    }
    return ViewController("web/index.html", **context).load()


@router.route("/login")
def login():
    context = {
        "title": "Login"
    }
    return ViewController("web/login.html", **context).load()


@router.route("/signup")
def signup():
    context = {
        "title": "Sign up"
    }
    return ViewController("web/signup.html", **context).load()


@router.route("/network")
def network():
    wg_ifaces = list(manager.interfaces.values())
    interfaces = get_all_interfaces(wg_bin=manager.config.linguard_options.wg_bin, wg_interfaces=wg_ifaces)
    routes = get_routing_table()
    context = {
        "title": "Network",
        "interfaces": interfaces,
        "routes": routes,
        "last_update": datetime.now().strftime("%H:%M"),
        "EMPTY_FIELD": EMPTY_FIELD
    }
    return ViewController("web/network.html", **context).load()


@router.route("/wireguard")
def wireguard():
    wg_ifaces = list(manager.interfaces.values())
    interfaces = get_wg_interfaces_summary(wg_bin=manager.config.linguard_options.wg_bin, interfaces=wg_ifaces)
    context = {
        "title": "Wireguard",
        "interfaces": interfaces,
        "last_update": datetime.now().strftime("%H:%M"),
        "EMPTY_FIELD": EMPTY_FIELD
    }
    return ViewController("web/wireguard.html", **context).load()


@router.route("/wireguard/interfaces/add", methods=['GET'])
def create_wireguard_iface():
    iface = manager.generate_interface()
    context = {
        "title": "Add interface",
        "iface": iface,
        "EMPTY_FIELD": EMPTY_FIELD,
        "APP_NAME": APP_NAME
    }
    return ViewController("web/wireguard-add-iface.html", **context).load()


@router.route("/wireguard/interfaces/add/<uuid>", methods=['POST'])
def add_wireguard_iface(uuid: str):
    data = request.json["data"]
    return RestController(manager, uuid).add_iface(data)


@router.route("/wireguard/interfaces/<uuid>", methods=['GET'])
def get_wireguard_iface(uuid: str):
    if uuid not in manager.interfaces:
        abort(NOT_FOUND, f"Unknown interface '{uuid}'.")
    iface = manager.interfaces[uuid]
    iface_status = get_wg_interface_status(manager.config.linguard_options.wg_bin, iface.name)
    context = {
        "title": "Edit interface",
        "iface": iface,
        "iface_status": iface_status,
        "last_update": datetime.now().strftime("%H:%M"),
        "EMPTY_FIELD": EMPTY_FIELD,
        "APP_NAME": APP_NAME
    }
    return ViewController("web/wireguard-iface.html", **context).load()


@router.route("/wireguard/interfaces/<uuid>/save", methods=['POST'])
def save_wireguard_iface(uuid: str):
    if uuid not in manager.interfaces:
        abort(NOT_FOUND, f"Interface {uuid} not found.")
    data = request.json["data"]
    return RestController(manager, uuid).apply_iface(data)


@router.route("/wireguard/interfaces/<uuid>/remove", methods=['DELETE'])
def remove_wireguard_iface(uuid: str):
    if uuid not in manager.interfaces:
        abort(NOT_FOUND, f"Interface {uuid} not found.")
    return RestController(manager, uuid).remove_iface()


@router.route("/wireguard/interfaces/<uuid>/regenerate-keys", methods=['POST'])
def regenerate_iface_keys(uuid: str):
    return RestController(manager, uuid).regenerate_iface_keys()


@router.route("/wireguard/interfaces/<uuid>", methods=['POST'])
def operate_wireguard_iface(uuid: str):
    action = request.json["action"].lower()
    try:
        if action == "start":
            manager.iface_up(uuid)
            return Response(status=NO_CONTENT)
        if action == "restart":
            manager.restart_iface(uuid)
            return Response(status=NO_CONTENT)
        if action == "stop":
            manager.iface_down(uuid)
            return Response(status=NO_CONTENT)
        raise WireguardError(f"Invalid operation: {action}", BAD_REQUEST)
    except WireguardError as e:
        return Response(e.cause, status=e.http_code)


@router.route("/wireguard/interfaces", methods=['POST'])
def operate_wireguard_ifaces():
    action = request.json["action"].lower()
    try:
        if action == "start":
            for iface in manager.interfaces.values():
                manager.iface_up(iface.uuid)
            return Response(status=NO_CONTENT)
        if action == "restart":
            for iface in manager.interfaces.values():
                manager.restart_iface(iface.uuid)
            return Response(status=NO_CONTENT)
        if action == "stop":
            for iface in manager.interfaces.values():
                manager.iface_down(iface.uuid)
            return Response(status=NO_CONTENT)
        raise WireguardError(f"invalid operation: {action}", BAD_REQUEST)
    except WireguardError as e:
        return Response(e.cause, status=e.http_code)


@router.route("/wireguard/peers/add", methods=['GET'])
def create_wireguard_peer():
    iface = None
    iface_uuid = request.args.get("interface")
    if iface_uuid:
        if iface_uuid not in manager.interfaces:
            abort(BAD_REQUEST, f"Unable to create peer for unknown interface '{iface_uuid}'.")
        iface = manager.interfaces[iface_uuid]
    peer = manager.generate_peer(iface)
    interfaces = get_wg_interfaces_summary(wg_bin=manager.config.linguard_options.wg_bin,
                                           interfaces=list(manager.interfaces.values())).values()
    context = {
        "title": "Add peer",
        "peer": peer,
        "interfaces": interfaces,
        "EMPTY_FIELD": EMPTY_FIELD,
        "APP_NAME": APP_NAME
    }
    return ViewController("web/wireguard-add-peer.html", **context).load()


@router.route("/wireguard/peers/add", methods=['POST'])
def add_wireguard_peer():
    data = request.json["data"]
    return RestController(manager).add_peer(data)


@router.route("/wireguard/peers/<uuid>/remove", methods=['DELETE'])
def remove_wireguard_peer(uuid: str):
    return RestController(manager).remove_peer(uuid)


@router.route("/wireguard/peers/<uuid>", methods=['GET'])
def get_wireguard_peer(uuid: str):
    peer = None
    for iface in manager.interfaces.values():
        if uuid in iface.peers:
            peer = iface.peers[uuid]
    if not peer:
        abort(NOT_FOUND, f"Unknown peer '{uuid}'.")
    context = {
        "title": "Edit peer",
        "peer": peer,
        "last_update": datetime.now().strftime("%H:%M"),
        "EMPTY_FIELD": EMPTY_FIELD,
        "APP_NAME": APP_NAME
    }
    return ViewController("web/wireguard-peer.html", **context).load()


@router.route("/wireguard/peers/<uuid>/save", methods=['POST'])
def save_wireguard_peers(uuid: str):
    data = request.json["data"]
    return RestController(manager, uuid).save_peer(data)


@router.route("/wireguard/peers/<uuid>/download", methods=['GET'])
def download_wireguard_peer(uuid: str):
    return RestController(manager, uuid).download_peer()


@router.route("/themes")
def themes():
    context = {
        "title": "Themes"
    }
    return ViewController("web/themes.html", **context).load()


@router.route("/settings")
def settings():
    context = {
        "title": "Settings",
        "config": manager.config,
        "config_filepath": manager.config_filepath
    }
    return ViewController("web/settings.html", **context).load()


@router.route("/settings/save", methods=['POST'])
def save_settings():
    data = request.json["data"]
    return RestController(manager).save_settings(data)


@router.app_errorhandler(BAD_REQUEST)
def bad_request(err):
    error_code = 400
    context = {
        "title": error_code,
        "error_code": error_code,
        "error_msg": str(err).split(":", 1)[1]
    }
    return ViewController("error/error-main.html", **context).load(), error_code


@router.app_errorhandler(UNAUTHORIZED)
def unauthorized(err):
    error_code = 401
    context = {
        "title": error_code,
        "error_code": error_code,
        "error_msg": str(err).split(":", 1)[1]
    }
    return ViewController("error/error-main.html", **context).load(), error_code


@router.app_errorhandler(NOT_FOUND)
def not_found(err):
    error_code = 404
    context = {
        "title": error_code,
        "error_code": error_code,
        "error_msg": str(err).split(":", 1)[1],
        "image": "/static/assets/img/error-404-monochrome.svg"
    }
    return ViewController("error/error-img.html", **context).load(), error_code


@router.app_errorhandler(INTERNAL_SERVER_ERROR)
def not_found(err):
    error_code = 500
    context = {
        "title": error_code,
        "error_code": error_code,
        "error_msg": str(err).split(":", 1)[1]
    }
    return ViewController("error/error-main.html", **context).load(), error_code
