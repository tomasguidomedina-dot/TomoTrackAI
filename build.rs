use pipl::*;

fn main() {
    pipl::plugin_build(vec![
        Property::Kind(PIPLType::AEEffect),
        Property::Name("TomoTrack Native Check"),
        Property::Category("Tomo FX"),
        #[cfg(target_os = "macos")]
        Property::CodeMacIntel64("EffectMain"),
        Property::AE_PiPL_Version { major: 2, minor: 0 },
        Property::AE_Effect_Spec_Version { major: 13, minor: 28 },
        Property::AE_Effect_Version {
            version: 0, subversion: 0, bugversion: 1,
            stage: Stage::Develop, build: 1,
        },
        Property::AE_Effect_Info_Flags(0),
        Property::AE_Effect_Global_OutFlags(
            OutFlags::PixIndependent | OutFlags::DeepColorAware
        ),
        Property::AE_Effect_Global_OutFlags_2(
            OutFlags2::FloatColorAware |
            OutFlags2::SupportsThreadedRendering |
            OutFlags2::SupportsGetFlattenedSequenceData
        ),
        Property::AE_Effect_Match_Name("TMFX TomoTrackNativeCheck"),
        Property::AE_Reserved_Info(0),
        Property::AE_Effect_Support_URL("https://github.com/tomasguidomedina-dot/TomoTrackAI"),
    ]);
}
