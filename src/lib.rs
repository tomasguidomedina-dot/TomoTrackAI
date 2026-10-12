//! Bootstrap de efecto nativo AE.
//! Prueba de carga/render: muestra un recuadro verde ajustable.
//! NO implementa todavía seguimiento automático de objetos.

use after_effects as ae;

#[derive(Eq, PartialEq, Hash, Clone, Copy, Debug)]
enum Params {
    CenterX,
    CenterY,
    BoxSize,
    ShowBox,
}

#[derive(Default)]
struct Plugin {}

ae::define_effect!(Plugin, (), Params);

impl AdobePluginGlobal for Plugin {
    fn params_setup(
        &self,
        params: &mut ae::Parameters<Params>,
        _in_data: ae::InData,
        _out_data: ae::OutData,
    ) -> Result<(), ae::Error> {
        for (kind, label, default) in [
            (Params::CenterX, "Centro X (%)", 50.0),
            (Params::CenterY, "Centro Y (%)", 50.0),
            (Params::BoxSize, "Tamano cuadro (px)", 160.0),
        ] {
            params.add(kind, label, ae::FloatSliderDef::setup(|f| {
                f.set_valid_min(0.0);
                f.set_slider_min(0.0);
                f.set_valid_max(if kind == Params::BoxSize { 1500.0 } else { 100.0 });
                f.set_slider_max(if kind == Params::BoxSize { 1500.0 } else { 100.0 });
                f.set_default(default);
                f.set_value(default);
                f.set_precision(1);
            }))?;
        }
        params.add(Params::ShowBox, "Mostrar cuadro", ae::CheckBoxDef::setup(|f| {
            f.set_default(true);
            f.set_value(true);
            f.set_label("Mostrar marcador de diagnostico");
        }))?;
        Ok(())
    }

    fn handle_command(
        &mut self,
        command: ae::Command,
        in_data: ae::InData,
        mut out_data: ae::OutData,
        params: &mut ae::Parameters<Params>,
    ) -> Result<(), ae::Error> {
        match command {
            ae::Command::About => {
                out_data.set_return_msg("TomoTrackAI 2.0 - Native Check 0.0.1\rPrueba de integracion nativa con AE; sin tracking automatico.");
            }
            ae::Command::Render { in_layer, mut out_layer } => {
                if !params.get(Params::ShowBox)?.as_checkbox()?.value() {
                    out_layer.copy_from(&in_layer, None, None)?;
                    return Ok(());
                }

                let x_pct = params.get(Params::CenterX)?.as_float_slider()?.value() as f32 / 100.0;
                let y_pct = params.get(Params::CenterY)?.as_float_slider()?.value() as f32 / 100.0;
                let side = params.get(Params::BoxSize)?.as_float_slider()?.value() as i32;
                let cx = (in_data.width() as f32 * x_pct).round() as i32;
                let cy = (in_data.height() as f32 * y_pct).round() as i32;
                let radius = (side / 2).max(0);
                let left = cx - radius;
                let right = cx + radius;
                let top = cy - radius;
                let bottom = cy + radius;

                in_layer.iterate_with(
                    &mut out_layer,
                    0,
                    in_data.height(),
                    None,
                    |x: i32, y: i32, inp: ae::GenericPixel, out: ae::GenericPixelMut| -> Result<(), ae::Error> {
                        let border = side > 0
                            && ((((x - left).abs() <= 1 || (x - right).abs() <= 1) && y >= top && y <= bottom)
                                || (((y - top).abs() <= 1 || (y - bottom).abs() <= 1) && x >= left && x <= right));
                        let center = (x - cx).abs() <= 2 && (y - cy).abs() <= 2;
                        let mark = border || center;
                        match (inp, out) {
                            (ae::GenericPixel::Pixel8(src), ae::GenericPixelMut::Pixel8(dst)) => {
                                dst.alpha = src.alpha;
                                dst.red = if mark { 0 } else { src.red };
                                dst.green = if mark { 255 } else { src.green };
                                dst.blue = if mark { 80 } else { src.blue };
                            }
                            (ae::GenericPixel::Pixel16(src), ae::GenericPixelMut::Pixel16(dst)) => {
                                dst.alpha = src.alpha;
                                dst.red = if mark { 0 } else { src.red };
                                dst.green = if mark { ae::MAX_CHANNEL16 as _ } else { src.green };
                                dst.blue = if mark { (ae::MAX_CHANNEL16 / 3) as _ } else { src.blue };
                            }
                            (ae::GenericPixel::PixelF32(src), ae::GenericPixelMut::PixelF32(dst)) => {
                                dst.alpha = src.alpha;
                                dst.red = if mark { 0.0 } else { src.red };
                                dst.green = if mark { 1.0 } else { src.green };
                                dst.blue = if mark { 0.32 } else { src.blue };
                            }
                            _ => return Err(ae::Error::BadCallbackParameter),
                        }
                        Ok(())
                    }
                )?;
            }
            _ => {}
        }
        Ok(())
    }
}
