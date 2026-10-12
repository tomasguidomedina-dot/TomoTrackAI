use pipl::*;

fn main() {
    // Etapa de diagnostico: sin MFR ni SmartRender; usamos Render legado.
    let flags2 = OutFlags2::empty();
    pipl::plugin_build(vec![
        Property::Kind(PIPLType::AEEffect),
        Property::Name("TomoTrack Native Check"),
        Property::Category("Tomo FX"),
        #[cfg(target_os = "macos")]
        Property::CodeMacIntel64("EffectMain"),
        Property::AE_PiPL_Version { major: 2, minor: 0 },
        Property::AE_Effect_Spec_Version { major: 13, minor: 28 },
        Property::AE_Effect_Version {
            version: 0, subversion: 0, bugversion: 3,
            stage: Stage::Develop, build: 1,
        },
        Property::AE_Effect_Info_Flags(0),
        Property::AE_Effect_Global_OutFlags(
            OutFlags::PixIndependent | OutFlags::DeepColorAware
        ),
        Property::AE_Effect_Global_OutFlags_2(flags2),
        Property::AE_Effect_Match_Name("TMFX TomoTrackNativeCheck"),
        Property::AE_Reserved_Info(0),
        Property::AE_Effect_Support_URL("https://github.com/tomasguidomedina-dot/TomoTrackAI"),
    ]);
}
