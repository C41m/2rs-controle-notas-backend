# app/core/email.py
import resend
from typing import List
from fastapi.concurrency import run_in_threadpool
from app.core.config import settings

# Configura a chave da API do Resend (só precisa fazer uma vez)
resend.api_key = settings.RESEND_API_KEY

if not resend.api_key:
    raise ValueError("RESEND_API_KEY não está definida nas variáveis de ambiente.")


def _send_email_sync(params: dict):
    """Função síncrona que chama a API do Resend."""
    return resend.Emails.send(params)


async def send_admin_notification(
    nota_id: int,
    cliente_nome: str,
    valor_total: float,
    descricao: str,
    usuario_emissor: str,
):
    """
    Envia e-mail de notificação ao administrador quando uma nova nota fiscal é emitida.
    Usa os e-mails configurados em ADMIN_EMAILS (string CSV).
    """
    # 👇 Converte a string "email1,email2" em lista
    admin_emails = [email.strip() for email in settings.ADMIN_EMAILS.split(",") if email.strip()]
    
    if not admin_emails:
        print("[EMAIL] Nenhum e-mail de administrador configurado.")
        return None

    html_content = f"""
    <h2>🔔 Nova Nota Fiscal Emitida</h2>
    <p><strong>ID da Nota:</strong> {nota_id}</p>
    <p><strong>Emitente:</strong> {usuario_emissor}</p>
    <p><strong>Cliente:</strong> {cliente_nome}</p>
    <p><strong>Valor Total:</strong> R$ {valor_total:,.2f}</p>
    <p><strong>Descrição:</strong> {descricao or "—"}</p>
    <p><em>Esta é uma notificação automática do sistema.</em></p>
    """

    params = {
        "from": settings.EMAIL_FROM,
        "to": admin_emails,
        "subject": f"Nova Nota Fiscal #{nota_id} Emitida",
        "html": html_content,
    }

    try:
        # Executa a chamada síncrona em thread (necessário em async context)
        response = await run_in_threadpool(_send_email_sync, params)
        print(f"[EMAIL] Notificação enviada com sucesso. ID: {response['id']}")
        return response
    except Exception as e:
        print(f"[ERRO EMAIL] Falha ao enviar notificação: {e}")
        return None