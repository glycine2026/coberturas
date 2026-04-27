"""
Módulo de cálculos para retenciones, FAS teórico y crushing
"""

def calcular_exportacion_grano(fob, cultivo='soja', precio_fas_manual=None):
    """
    Calcula FAS teórico para exportación de grano
    
    Args:
        fob (float): Precio FOB en USD/tn
        cultivo (str): Tipo de cultivo (soja, maiz, trigo, girasol)
        precio_fas_manual (float, optional): Precio FAS objetivo manual
        
    Returns:
        dict: Resultados del cálculo
    """
    
    # Parámetros según cultivo
    parametros = {
        'soja': {'retencion_pct': 26.0, 'fobbing': 12.0},
        'maiz': {'retencion_pct': 7.0, 'fobbing': 11.0},
        'trigo': {'retencion_pct': 7.0, 'fobbing': 13.0},
        'girasol': {'retencion_pct': 7.0, 'fobbing': 14.0}
    }
    
    params = parametros.get(cultivo, parametros['soja'])
    
    # Cálculos
    retencion_valor = fob * (params['retencion_pct'] / 100)
    fobbing = params['fobbing']
    fas_teorico = fob - retencion_valor - fobbing
    
    # Spread si hay precio manual
    spread = None
    if precio_fas_manual:
        spread = fas_teorico - precio_fas_manual
    
    return {
        'fob_indice': fob,
        'retencion_pct': params['retencion_pct'],
        'retencion_valor': retencion_valor,
        'fobbing': fobbing,
        'fas_teorico': fas_teorico,
        'precio_fas_manual': precio_fas_manual,
        'spread': spread
    }


def calcular_crushing(fob_aceite, fob_harina, coef_aceite=0.19, coef_harina=0.78,
                     ret_subprod_pct=22.5, fobbing_subprod=19.0, gto_ind=29.0):
    """
    Calcula FAS para crushing de soja
    
    Args:
        fob_aceite (float): Precio FOB aceite
        fob_harina (float): Precio FOB harina
        coef_aceite (float): Coeficiente de aceite
        coef_harina (float): Coeficiente de harina
        ret_subprod_pct (float): Retención subproductos %
        fobbing_subprod (float): Fobbing subproductos
        gto_ind (float): Gasto industrial
        
    Returns:
        dict: Resultados del cálculo de crushing
    """
    
    # Valores brutos
    aceite_bruto = fob_aceite * coef_aceite
    harina_bruta = fob_harina * coef_harina
    valor_bruto_total = aceite_bruto + harina_bruta
    
    # Deducciones
    retencion_subprod = valor_bruto_total * (ret_subprod_pct / 100)
    
    # FAS Crushing
    fas_crushing = valor_bruto_total - retencion_subprod - fobbing_subprod - gto_ind
    
    return {
        'fob_aceite': fob_aceite,
        'fob_harina': fob_harina,
        'coef_aceite': coef_aceite,
        'coef_harina': coef_harina,
        'aceite_bruto': aceite_bruto,
        'harina_bruta': harina_bruta,
        'valor_bruto_total': valor_bruto_total,
        'retencion_pct': ret_subprod_pct,
        'retencion_valor': retencion_subprod,
        'fobbing_subprod': fobbing_subprod,
        'gto_ind': gto_ind,
        'fas_crushing': fas_crushing
    }


def calcular_retenciones(fob, cultivo='soja'):
    """
    Calcula retenciones según cultivo
    
    Args:
        fob (float): Precio FOB
        cultivo (str): Tipo de cultivo
        
    Returns:
        dict: Valor y porcentaje de retención
    """
    
    retenciones_pct = {
        'soja': 26.0,
        'maiz': 7.0,
        'trigo': 7.0,
        'girasol': 7.0
    }
    
    pct = retenciones_pct.get(cultivo, 0)
    valor = fob * (pct / 100)
    
    return {
        'porcentaje': pct,
        'valor': valor,
        'fob_neto': fob - valor
    }


def calcular_fas_teorico(fob, cultivo='soja', fobbing=12.0):
    """
    Calcula FAS teórico (versión simplificada)
    
    Args:
        fob (float): Precio FOB
        cultivo (str): Tipo de cultivo
        fobbing (float): Costo de fobbing
        
    Returns:
        float: FAS teórico
    """
    
    ret_info = calcular_retenciones(fob, cultivo)
    fas = ret_info['fob_neto'] - fobbing
    
    return fas


def calcular_spread_crushing(fob_aceite, fob_harina, fob_soja, cultivo='soja'):
    """
    Calcula el spread entre crushing y exportación de grano
    
    Args:
        fob_aceite (float): Precio FOB aceite
        fob_harina (float): Precio FOB harina
        fob_soja (float): Precio FOB soja
        cultivo (str): Tipo de cultivo
        
    Returns:
        dict: Spread y recomendación
    """
    
    # Calcular FAS grano
    grano = calcular_exportacion_grano(fob_soja, cultivo)
    
    # Calcular FAS crushing
    crushing = calcular_crushing(fob_aceite, fob_harina)
    
    # Spread
    spread = crushing['fas_crushing'] - grano['fas_teorico']
    
    # Recomendación
    if spread > 0:
        recomendacion = "CRUSHING"
        razon = f"El crushing genera ${spread:.2f} más por tonelada"
    else:
        recomendacion = "EXPORTACIÓN GRANO"
        razon = f"La exportación grano genera ${abs(spread):.2f} más por tonelada"
    
    return {
        'fas_grano': grano['fas_teorico'],
        'fas_crushing': crushing['fas_crushing'],
        'spread': spread,
        'recomendacion': recomendacion,
        'razon': razon
    }
