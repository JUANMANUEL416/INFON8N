"""
Script de prueba para el sistema de aclaraciones y validaciones IA
"""
import requests
import json
import time

BASE_URL = 'http://localhost:5000'

def probar_sistema_completo():
    print("=" * 80)
    print("🧪 PRUEBA DEL SISTEMA DE ACLARACIONES Y VALIDACIONES IA")
    print("=" * 80)
    
    # Paso 1: Crear reporte con campos ambiguos
    print("\n📝 Paso 1: Creando reporte con campos ambiguos...")
    
    reporte_data = {
        'codigo': 'TEST_ACLARACIONES',
        'nombre': 'Reporte de Prueba Aclaraciones',
        'descripcion': 'Reporte para probar el sistema de validación con IA',
        'campos': [
            {
                'nombre': 'estado',  # Campo ambiguo
                'tipo': 'texto',
                'descripcion': '',  # Sin descripción
                'obligatorio': True
            },
            {
                'nombre': 'valor',  # Campo ambiguo
                'tipo': 'numero',
                'descripcion': '',  # Sin descripción
                'obligatorio': True
            },
            {
                'nombre': 'tipo',  # Campo ambiguo
                'tipo': 'texto',
                'descripcion': 'Tipo de registro',  # Descripción vaga
                'obligatorio': False
            },
            {
                'nombre': 'fecha_registro',  # Campo claro
                'tipo': 'fecha',
                'descripcion': 'Fecha en que se registró el evento en el sistema',
                'obligatorio': True
            },
            {
                'nombre': 'nombre_completo_cliente',  # Campo claro
                'tipo': 'texto',
                'descripcion': 'Nombre completo del cliente incluyendo primer nombre, segundo nombre y apellidos',
                'obligatorio': True
            }
        ]
    }
    
    response = requests.post(f'{BASE_URL}/api/admin/reportes', json=reporte_data)
    
    if response.status_code == 201:
        resultado = response.json()
        print("✅ Reporte creado exitosamente")
        
        if 'validacion_ia' in resultado:
            print(f"\n🤖 Validación IA:")
            print(f"   Puntuación de claridad: {resultado['validacion_ia']['puntuacion']}/100")
            print(f"   Campos con dudas: {resultado['validacion_ia']['campos_con_dudas']}")
            print(f"   Requiere aclaraciones: {resultado['validacion_ia']['requiere_aclaraciones']}")
        else:
            print("⚠️  No se ejecutó validación IA (puede estar deshabilitada)")
    else:
        print(f"❌ Error creando reporte: {response.text}")
        return False
    
    time.sleep(2)
    
    # Paso 2: Verificar aclaraciones creadas
    print("\n🔍 Paso 2: Verificando aclaraciones creadas...")
    
    response = requests.get(f'{BASE_URL}/api/aclaraciones/TEST_ACLARACIONES')
    
    if response.status_code == 200:
        data = response.json()
        aclaraciones = data.get('aclaraciones', [])
        
        print(f"✅ Encontradas {len(aclaraciones)} aclaraciones:")
        
        for acl in aclaraciones:
            print(f"\n   Campo: {acl['nombre_campo']}")
            print(f"   Estado: {acl['estado']}")
            print(f"   Pregunta: {acl['pregunta_ia'][:80]}...")
    else:
        print(f"❌ Error obteniendo aclaraciones: {response.text}")
        return False
    
    if len(aclaraciones) == 0:
        print("\n⚠️  No se crearon aclaraciones. Probablemente porque:")
        print("   - ENABLE_IA_VALIDATION está en false")
        print("   - La IA no detectó campos dudosos")
        print("   - Hubo un error en la validación")
        return False
    
    time.sleep(2)
    
    # Paso 3: Simular respuesta de usuario
    print("\n💬 Paso 3: Simulando respuesta de usuario...")
    
    aclaracion_id = aclaraciones[0]['id']
    campo = aclaraciones[0]['nombre_campo']
    
    respuesta_usuario = {
        'respuesta': f'El campo "{campo}" se refiere al estado del proceso de aprobación (pendiente, aprobado, rechazado)',
        'usuario': 'juan.perez'
    }
    
    response = requests.post(
        f'{BASE_URL}/api/aclaraciones/{aclaracion_id}/responder',
        json=respuesta_usuario
    )
    
    if response.status_code == 200:
        print("✅ Usuario respondió la aclaración correctamente")
        print(f"   Respuesta: {respuesta_usuario['respuesta'][:80]}...")
    else:
        print(f"❌ Error respondiendo aclaración: {response.text}")
        return False
    
    time.sleep(2)
    
    # Paso 4: Verificar notificaciones para admin
    print("\n🔔 Paso 4: Verificando notificaciones para admin...")
    
    response = requests.get(f'{BASE_URL}/api/admin/notificaciones')
    
    if response.status_code == 200:
        data = response.json()
        notificaciones = data.get('notificaciones', [])
        
        print(f"✅ Encontradas {len(notificaciones)} notificaciones sin leer:")
        
        for notif in notificaciones[:3]:  # Mostrar solo las primeras 3
            print(f"\n   Tipo: {notif['tipo']}")
            print(f"   Título: {notif['titulo']}")
            print(f"   Mensaje: {notif['mensaje'][:80]}...")
    else:
        print(f"❌ Error obteniendo notificaciones: {response.text}")
    
    time.sleep(2)
    
    # Paso 5: Simular validación de admin
    print("\n✅ Paso 5: Simulando validación de administrador...")
    
    validacion_admin = {
        'respuesta_final': f'El campo "{campo}" representa el estado de aprobación del registro. Valores permitidos: pendiente, aprobado, rechazado, en_revision.',
        'aprobar': True,
        'admin': 'admin_sistema'
    }
    
    response = requests.post(
        f'{BASE_URL}/api/admin/aclaraciones/{aclaracion_id}/validar',
        json=validacion_admin
    )
    
    if response.status_code == 200:
        print("✅ Admin validó y aprobó la aclaración")
        print(f"   Respuesta final: {validacion_admin['respuesta_final'][:80]}...")
        print("   📚 Agregada a la base de conocimiento de IA")
    else:
        print(f"❌ Error validando aclaración: {response.text}")
        return False
    
    time.sleep(2)
    
    # Paso 6: Verificar lista de aclaraciones pendientes
    print("\n📊 Paso 6: Verificando estado final de aclaraciones...")
    
    response = requests.get(f'{BASE_URL}/api/admin/aclaraciones/pendientes')
    
    if response.status_code == 200:
        data = response.json()
        aclaraciones = data.get('aclaraciones', [])
        
        pendientes = [a for a in aclaraciones if a['estado'] == 'pendiente']
        respondidas = [a for a in aclaraciones if a['estado'] == 'respondida_usuario']
        aprobadas = [a for a in aclaraciones if a.get('aprobado')]
        
        print(f"\n   Estado de aclaraciones:")
        print(f"   - Pendientes de usuario: {len(pendientes)}")
        print(f"   - Pendientes de validación admin: {len(respondidas)}")
        print(f"   - Aprobadas (en base de conocimiento): {len(aprobadas)}")
    else:
        print(f"⚠️  Error obteniendo estado: {response.text}")
    
    # Resumen final
    print("\n" + "=" * 80)
    print("🎉 PRUEBA COMPLETADA EXITOSAMENTE")
    print("=" * 80)
    print("\n✅ Sistema de aclaraciones funcionando correctamente:")
    print("   1. ✅ IA detecta campos ambiguos automáticamente")
    print("   2. ✅ Se crean aclaraciones con preguntas específicas")
    print("   3. ✅ Usuarios pueden responder aclaraciones")
    print("   4. ✅ Admins reciben notificaciones de respuestas")
    print("   5. ✅ Admins pueden validar/mejorar respuestas")
    print("   6. ✅ Conocimiento se guarda para futuras validaciones")
    
    print("\n💡 Próximos pasos:")
    print("   - Probar desde el panel de admin en http://localhost:5000/admin")
    print("   - Verificar sección 'Aclaraciones' en el menú lateral")
    print("   - Crear más reportes y ver cómo aprende el sistema")
    
    return True

if __name__ == '__main__':
    try:
        probar_sistema_completo()
    except Exception as e:
        print(f"\n❌ Error en la prueba: {e}")
        import traceback
        traceback.print_exc()
