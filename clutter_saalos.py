import math

from clutter_constants import MAX_CLUTTER_LOSS

EARTH_RADIUS = 6378137.0


def clutter_loss_saalos(d__meter, cch__meter, h_tx__meter, h_rx__meter,
                        h_rx_gnd__meter, pol, f__mhz):
    if cch__meter <= 0.0:
        return 0.0
    if d__meter == 0.0:
        return 0.0
    if h_rx__meter > cch__meter:
        return 0.0

    wn = f__mhz / 47.7
    pd = d__meter
    pdk = pd / 1000.0

    hone = h_tx__meter
    arte = 0.0

    if h_tx__meter > cch__meter:
        ensa = 1.0
        encca = 1.0
        dp = pd
        d1a = pd
        crpc = pd
        cttc = 1.0
        ssnps = 0.0
        ctic = 1.0
        ttc = 0.0
        tic = 0.0
        tsp = 1.0
        rsp = 0.0

        for _ in range(5):
            tde = dp / EARTH_RADIUS
            hc = (cch__meter + EARTH_RADIUS) * (1.0 - math.cos(tde))
            dx = (cch__meter + EARTH_RADIUS) * math.sin(tde)
            ucrpc = math.sqrt((hone - cch__meter + hc) ** 2 + dx * dx)
            ctip = (hone - cch__meter + hc) / ucrpc
            tip = math.acos(ctip)
            tic = max(0.0, tip + tde)
            stic = math.sin(tic)
            sta = (ensa / encca) * stic
            ttc = math.asin(sta)
            cttc = math.sqrt(1.0 - math.sin(ttc) ** 2)
            crpc = (cch__meter - h_rx__meter) / cttc
            if crpc >= dp:
                crpc = dp - 1.0 / dp
            ssnps = (math.pi / 2.0) - tic
            d1a = (crpc * math.sin(ttc)) / (1.0 - 1.0 / EARTH_RADIUS)
            dp = pd - d1a

        ctic = math.cos(tic)

        if ssnps <= 0.0:
            d1a = min(0.1 * pd, 600.0)
            crpc = d1a
            hone = cch__meter + 1.0
            rsp = 0.997
            tsp = 1.0 - rsp
        elif pol == 1:
            q = (ensa * cttc - encca * ctic) / (ensa * cttc + encca * ctic)
            rsp = q * q
            tsp = 1.0 - rsp
        elif pol == 2:
            q1 = (ensa * ctic - encca * cttc) / (ensa * ctic + encca * cttc)
            q2 = (ensa * cttc - encca * ctic) / (ensa * cttc + encca * ctic)
            rsp = (q1 * q1 + q2 * q2) / 2.0
            tsp = 1.0 - rsp
        else:
            q = (ensa * ctic - encca * cttc) / (ensa * ctic + encca * ctic)
            rsp = q * q
            tsp = 1.0 - rsp

        tvsr = max(0.0, h_tx__meter - h_rx_gnd__meter)

        if d1a < 50.0:
            arte = 0.0195 * crpc - 20.0 * math.log10(tsp)
        elif d1a < 225.0:
            if tvsr > 1000.0:
                q = d1a * (0.03 * math.exp(-0.14 * pdk))
            else:
                q = d1a * (0.07 * math.exp(-0.17 * pdk))
            arte = q + (0.7 * pdk - max(0.01, math.log10(wn * 47.7) - 2.0)) * (h_rx__meter / hone)
        else:
            q = 0.00055 * pdk + math.log10(pdk) * (0.041 - 0.0017 * math.sqrt(hone) + 0.019)
            arte = d1a * q - (18.0 * math.log10(rsp)) / math.exp(hone / 37.5)
            zi = 1.5 * math.sqrt(hone - cch__meter)
            if pdk > zi:
                q = (pdk - zi) * 10.2 * math.sqrt(max(0.01, math.log10(wn * 47.7) - 2.0)) / (100.0 - zi)
            else:
                q = ((zi - pdk) / zi) * (-20.0 * max(0.01, math.log10(wn * 47.7) - 2.0)) / math.sqrt(hone)
            arte = arte + q
    else:
        q1 = (cch__meter - h_tx__meter) * (2.06943 - 1.56184 * math.exp(1.0 / cch__meter - h_tx__meter))
        q2 = (17.98 - 0.84224 * (cch__meter - h_tx__meter)) * math.exp(-0.00000061 * pd)
        arte = q1 + q2 + 1.34795 * 20.0 * math.log10(pd + 1.0)
        arte -= max(0.01, math.log10(wn * 47.7) - 2.0) * (h_rx__meter / h_tx__meter)

    if arte < 0.0:
        return 0.0
    if arte > MAX_CLUTTER_LOSS:
        return MAX_CLUTTER_LOSS
    return arte