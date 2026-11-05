from kivy.clock import mainthread
from kivy.utils import platform


def tem_camera():
    if platform != 'android':
        return True
    from android.permissions import Permission, check_permission
    return check_permission(Permission.CAMERA)


def pedir_camera(ao_responder):
    if platform != 'android':
        ao_responder(True)
        return
    from android.permissions import Permission, check_permission, request_permissions
    if check_permission(Permission.CAMERA):
        ao_responder(True)
        return

    def resposta(permissoes, concedidas):
        _responder(ao_responder, bool(concedidas) and all(concedidas))

    request_permissions([Permission.CAMERA], resposta)


@mainthread
def _responder(ao_responder, concedida):
    ao_responder(concedida)


def abrir_configuracoes_do_app():
    if platform != 'android':
        return False
    from android import mActivity
    from jnius import autoclass
    Intent = autoclass('android.content.Intent')
    Settings = autoclass('android.provider.Settings')
    Uri = autoclass('android.net.Uri')
    intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
    intent.setData(Uri.fromParts('package', mActivity.getPackageName(), None))
    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    mActivity.startActivity(intent)
    return True
