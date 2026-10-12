//! TomoTrack Native Check 0.0.3 — verificacion VISUAL del Render callback.
//! No contiene todavia un tracker: esta version debe mostrar
//! un tinte verde, un marco exterior y un recuadro central.

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

        params.add(Params::ShowBox, "Mostrar diagnostico", ae::CheckBoxDef::setup(|f| {
            f.set_default(true);
            f.set_value(true);
            f.set_label("Ver marco y tinte verde");
        }))?;
        Ok(())
    }

    fn handle_command(
        &mut self,
        command: ae::Command,
        _in_data: ae::InData,
        mut out_data: ae::OutData,
        params: &mut ae::Parameters<Params>,
    ) -> Result<(), ae::Error> {
        match command {
            ae::Command::About => {
                out_data.set_return_msg(
                    "TomoTrackAI - Native Check v0.0.3\rPrueba visual del render; todavia sin seguimiento automatico."
                );
            }
            ae::Command::Render { in_layer, mut out_layer } => {
                // Siempre copiar el fotograma original: no modificar el origen.
                out_layer.copy_from(&in_layer, None, None)?;

                // Marco y tinte SIEMPRE activos: validan el Render callback incluso
                // si AE recupero un valor antiguo del checkbox del proyecto.
                let show_square = params.get(Params::ShowBox)?.as_checkbox()?.value();

                // Usar la dimension REAL del buffer de salida, no la composicion.
                let width = out_layer.width() as i32;
                let height = out_layer.height() as i32;
                if width <= 0 || height <= 0 {
                    return Ok(());
                }

                let x_pct = (params.get(Params::CenterX)?.as_float_slider()?.value()
                    as f32 / 100.0).clamp(0.0, 1.0);
                let y_pct = (params.get(Params::CenterY)?.as_float_slider()?.value()
                    as f32 / 100.0).clamp(0.0, 1.0);
                let side = (params.get(Params::BoxSize)?.as_float_slider()?.value()
                    as i32).max(12);
                let cx = ((width - 1) as f32 * x_pct).round() as i32;
                let cy = ((height - 1) as f32 * y_pct).round() as i32;
                let half = side / 2;
                let left = cx - half;
                let right = cx + half;
                let top = cy - half;
                let bottom = cy + half;
                let thickness = 5;

                // Modificar el buffer de salida en el callback de render:
                // - leve tinte verde en toda la capa (prueba inequivoca de render)
                // - marco verde exterior, cuadro verde y cruz central.
                out_layer.iterate(0, height, None, move |x, y, px| {
                    let outer = x < thickness || y < thickness
                        || x >= width - thickness || y >= height - thickness;
                    let square = ((x - left).abs() <= thickness
                            || (x - right).abs() <= thickness)
                            && y >= top && y <= bottom
                        || ((y - top).abs() <= thickness
                            || (y - bottom).abs() <= thickness)
                            && x >= left && x <= right;
                    let cross = ((x - cx).abs() <= 12 && (y - cy).abs() <= 2)
                            || ((x - cx).abs() <= 2 && (y - cy).abs() <= 12);
                    let marked = outer || (show_square && (square || cross));

                    match px {
                        ae::GenericPixelMut::Pixel8(p) => {
                            if marked {
                                p.red = 0;
                                p.green = 255;
                                p.blue = 40;
                            } else {
                                p.green = p.green.saturating_add(45);
                            }
                        }
                        ae::GenericPixelMut::Pixel16(p) => {
                            if marked {
                                p.red = 0;
                                p.green = ae::MAX_CHANNEL16 as _;
                                p.blue = (ae::MAX_CHANNEL16 / 6) as _;
                            } else {
                                p.green = p.green.saturating_add((ae::MAX_CHANNEL16 / 6) as _);
                            }
                        }
                        ae::GenericPixelMut::PixelF32(p) => {
                            if marked {
                                p.red = 0.0;
                                p.green = 1.0;
                                p.blue = 0.15;
                            } else {
                                p.green += 0.17;
                            }
                        }
                        _ => return Err(ae::Error::BadCallbackParameter),
                    }
                    Ok(())
                })?;
            }
            _ => {}
        }
        Ok(())
    }
}
