//! TomoTrack ROI Select 0.1.0
//! Seleccion nativa de una region objetivo con Point Control de AE.
//! Aun no hace seguimiento temporal. Coexiste con Native Check v0.0.3.

use after_effects as ae;

#[derive(Eq, PartialEq, Hash, Clone, Copy, Debug)]
enum Params {
    Target,
    RoiWidth,
    RoiHeight,
    ShowRegion,
}

#[derive(Default)]
struct Plugin {}

ae::define_effect!(Plugin, (), Params);

impl AdobePluginGlobal for Plugin {
    fn params_setup(
        &self,
        params: &mut ae::Parameters<Params>,
        in_data: ae::InData,
        _out_data: ae::OutData,
    ) -> Result<(), ae::Error> {
        let center_x = (in_data.width().max(0) as f32) / 2.0;
        let center_y = (in_data.height().max(0) as f32) / 2.0;

        // AE muestra el control de punto sobre el metraje y deja arrastrarlo
        // con el raton. Defaults porcentuales; values en pixeles fuente.
        params.add(Params::Target, "Punto objetivo", ae::PointDef::setup(|f| {
            f.set_default((50.0, 50.0));
            f.set_value((center_x, center_y));
            f.set_restrict_bounds(true);
        }))?;

        params.add(Params::RoiWidth, "Ancho region (px)", ae::FloatSliderDef::setup(|f| {
            f.set_valid_min(16.0);
            f.set_slider_min(16.0);
            f.set_valid_max(3000.0);
            f.set_slider_max(1000.0);
            f.set_default(160.0);
            f.set_value(160.0);
            f.set_precision(0);
        }))?;

        params.add(Params::RoiHeight, "Alto region (px)", ae::FloatSliderDef::setup(|f| {
            f.set_valid_min(16.0);
            f.set_slider_min(16.0);
            f.set_valid_max(3000.0);
            f.set_slider_max(1000.0);
            f.set_default(120.0);
            f.set_value(120.0);
            f.set_precision(0);
        }))?;

        params.add(Params::ShowRegion, "Mostrar region", ae::CheckBoxDef::setup(|f| {
            f.set_default(true);
            f.set_value(true);
            f.set_label("Mostrar contorno de seleccion");
        }))?;
        Ok(())
    }

    fn handle_command(
        &mut self,
        cmd: ae::Command,
        _in_data: ae::InData,
        mut out_data: ae::OutData,
        params: &mut ae::Parameters<Params>,
    ) -> Result<(), ae::Error> {
        match cmd {
            ae::Command::About => out_data.set_return_msg(
                "TomoTrack ROI Select v0.1.0\rSeleccion de region nativa de AE; tracking automatico pendiente."
            ),
            ae::Command::Render { in_layer, mut out_layer } => {
                out_layer.copy_from(&in_layer, None, None)?;

                if !params.get(Params::ShowRegion)?.as_checkbox()?.value() {
                    return Ok(());
                }

                let width = out_layer.width() as i32;
                let height = out_layer.height() as i32;
                if width <= 0 || height <= 0 { return Ok(()); }

                let (x, y) = params.get(Params::Target)?.as_point()?.value();
                let cx = x.round() as i32;
                let cy = y.round() as i32;
                let half_w = (params.get(Params::RoiWidth)?
                    .as_float_slider()?.value() as i32).clamp(16, 3000) / 2;
                let half_h = (params.get(Params::RoiHeight)?
                    .as_float_slider()?.value() as i32).clamp(16, 3000) / 2;

                let left = cx - half_w;
                let right = cx + half_w;
                let top = cy - half_h;
                let bottom = cy + half_h;
                let thick = 3;
                out_layer.iterate(0, height, None, move |px, py, dest| {
                    let h_edge = (py - top).abs() <= thick
                        || (py - bottom).abs() <= thick;
                    let v_edge = (px - left).abs() <= thick
                        || (px - right).abs() <= thick;
                    let edge = (h_edge && px >= left && px <= right)
                        || (v_edge && py >= top && py <= bottom);
                    let cross = ((px - cx).abs() <= 13 && (py - cy).abs() <= 2)
                        || ((py - cy).abs() <= 13 && (px - cx).abs() <= 2);
                    if edge || cross {
                        match dest {
                            ae::GenericPixelMut::Pixel8(p) => {
                                p.red = if cross { 255 } else { 20 };
                                p.green = if cross { 200 } else { 255 };
                                p.blue = 255;
                            }
                            ae::GenericPixelMut::Pixel16(p) => {
                                p.red = if cross { ae::MAX_CHANNEL16 as _ } else { 0 };
                                p.green = ae::MAX_CHANNEL16 as _;
                                p.blue = ae::MAX_CHANNEL16 as _;
                            }
                            ae::GenericPixelMut::PixelF32(p) => {
                                p.red = if cross { 1.0 } else { 0.08 };
                                p.green = 1.0;
                                p.blue = 1.0;
                            }
                            _ => return Err(ae::Error::BadCallbackParameter),
                        }
                    }
                    Ok(())
                })?;
            }
            _ => {}
        }
        Ok(())
    }
}
