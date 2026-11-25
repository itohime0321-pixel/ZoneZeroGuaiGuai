"""Materialize the v0.1.7 source from the verified original archive and v0.1.4 model generator.
Run after upgrade_model.py. The nine synthetic pouch sounds are generated locally.
"""
import json, pathlib, sys, math, random, wave, struct, subprocess, tempfile
root=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'guai_guai_source')
java=root/'src/main/java/tw/zonezero/guaiguai'
assets=root/'src/main/resources/assets/guaiguai'
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(s,encoding='utf-8')
def replace(s,old,new):
    assert old in s, old
    return s.replace(old,new,1)
p=java/'AuraBlock.java'
s=p.read_text()
s=replace(s,'import net.minecraft.world.level.Level;','''import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.SimpleWaterloggedBlock;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.level.material.FluidState;
import net.minecraft.world.level.material.Fluids;
import java.util.function.Predicate;''')
s=replace(s,'extends Block {','extends Block implements SimpleWaterloggedBlock {')
s=replace(s,'private static final double RADIUS = 3.0;','''public static final BooleanProperty WATERLOGGED = BlockStateProperties.WATERLOGGED;
    private static final double RADIUS = 7.0;
    private static final int DIRECT_PLAYER_LIMIT = 32;
    private static final Predicate<ServerPlayer> ACTIVE_PLAYER = p -> p.isAlive() && !p.isSpectator();''')
s=replace(s,'setValue(FACING, Direction.NORTH));','setValue(FACING, Direction.NORTH).setValue(WATERLOGGED, false));')
s=replace(s,'builder.add(FACING);','builder.add(FACING, WATERLOGGED);')
s=replace(s,'return defaultBlockState().setValue(FACING, context.getHorizontalDirection().getOpposite());','''return defaultBlockState().setValue(FACING, context.getHorizontalDirection().getOpposite())
                .setValue(WATERLOGGED, context.getLevel().getFluidState(context.getClickedPos()).getType() == Fluids.WATER);''')
s=replace(s,'    @Override protected BlockState rotate','''    @Override protected FluidState getFluidState(BlockState state) {
        return state.getValue(WATERLOGGED) ? Fluids.WATER.getSource(false) : super.getFluidState(state);
    }
    @Override protected boolean canSurvive(BlockState state, LevelReader level, BlockPos pos) {
        return Block.canSupportCenter(level, pos.below(), Direction.UP);
    }
    @Override protected BlockState updateShape(BlockState state, Direction direction, BlockState neighbor,
                                               LevelAccessor level, BlockPos pos, BlockPos neighborPos) {
        if (state.getValue(WATERLOGGED)) {
            level.scheduleTick(pos, Fluids.WATER, Fluids.WATER.getTickDelay(level));
        }
        if (direction == Direction.DOWN && !state.canSurvive(level, pos)) {
            return Blocks.AIR.defaultBlockState();
        }
        return super.updateShape(state, direction, neighbor, level, pos, neighborPos);
    }
    @Override public int getFlammability(BlockState state, BlockGetter level, BlockPos pos, Direction face) {
        return state.getValue(WATERLOGGED) ? 0 : 60;
    }
    @Override public int getFireSpreadSpeed(BlockState state, BlockGetter level, BlockPos pos, Direction face) {
        return state.getValue(WATERLOGGED) ? 0 : 30;
    }
    @Override public boolean isFlammable(BlockState state, BlockGetter level, BlockPos pos, Direction face) {
        return !state.getValue(WATERLOGGED);
    }
    @Override public boolean ignitedByLava(BlockState state, BlockGetter level, BlockPos pos, Direction face) {
        return !state.getValue(WATERLOGGED);
    }
    @Override protected BlockState rotate''')
s=replace(s,'1 + Math.floorMod(pos.hashCode(), INTERVAL)','AuraTiming.initialDelay(pos.asLong(), INTERVAL)')
start=s.index('        if (!level.getBlockState(pos).is(this)) return;')
end=s.index('    @Override public void appendHoverText',start)
s=s[:start]+'''        if (!state.canSurvive(level, pos)) {
            level.destroyBlock(pos, true);
            return;
        }
        level.scheduleTick(pos, this, INTERVAL);
        List<ServerPlayer> players = level.players();
        int count = players.size();
        if (count == 0) return;
        double x = pos.getX() + 0.5;
        double y = pos.getY() + 0.5;
        double z = pos.getZ() + 0.5;
        Holder<MobEffect> type = effect.get();
        if (count <= DIRECT_PLAYER_LIMIT) {
            for (int i = 0; i < count; i++) {
                applyIfNearby(players.get(i), type, x, y, z);
            }
        } else {
            AABB area = new AABB(x-RADIUS, y-RADIUS, z-RADIUS,
                                 x+RADIUS, y+RADIUS, z+RADIUS);
            for (ServerPlayer player : level.getEntitiesOfClass(ServerPlayer.class, area, ACTIVE_PLAYER)) {
                applyIfNearby(player, type, x, y, z);
            }
        }
    }
    private void applyIfNearby(ServerPlayer player, Holder<MobEffect> type, double x, double y, double z) {
        if (!AuraTiming.withinRadius(player.getX()-x, player.getY()-y, player.getZ()-z, RADIUS)
                || !ACTIVE_PLAYER.test(player)) return;
        MobEffectInstance current = player.getEffect(type);
        if (current == null || AuraTiming.shouldRefresh(current.getAmplifier(),
                current.isInfiniteDuration(), current.getDuration(), duration)) {
            player.addEffect(new MobEffectInstance(type, duration, 0, true, false, true));
        }
    }
'''+s[end:]
s=replace(s,'''        tooltip.add(Component.translatable("tooltip.guaiguai." + color).withStyle(ChatFormatting.GREEN));
        tooltip.add(Component.translatable("tooltip.guaiguai.aura").withStyle(ChatFormatting.GRAY));''','''        tooltip.add(Component.translatable("tooltip.guaiguai." + color).withStyle(ChatFormatting.GRAY));
        if ("green".equals(color)) {
            tooltip.add(Component.translatable("tooltip.guaiguai.green.tradition").withStyle(ChatFormatting.GRAY));
        }''')
write(p,s)
write(java/'AuraTiming.java','''package tw.zonezero.guaiguai;

final class AuraTiming {
    private static final int REFRESH_TOLERANCE = 20;
    private AuraTiming() {}
    static int initialDelay(long packedPosition, int interval) {
        long x = packedPosition + 0x9E3779B97F4A7C15L;
        x = (x ^ (x >>> 30)) * 0xBF58476D1CE4E5B9L;
        x = (x ^ (x >>> 27)) * 0x94D049BB133111EBL;
        x ^= x >>> 31;
        return 1 + (int) Math.floorMod(x, (long) interval);
    }
    static boolean withinRadius(double dx, double dy, double dz, double radius) {
        return dx * dx + dy * dy + dz * dz <= radius * radius;
    }
    static boolean shouldRefresh(int amplifier, boolean infinite, int remaining, int duration) {
        return amplifier == 0 && !infinite && remaining <= duration - REFRESH_TOLERANCE;
    }
}
''')
p=java/'GuaiGuai.java'
s=p.read_text()
s=replace(s,'import net.minecraft.network.chat.Component;','''import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.level.material.PushReaction;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.common.util.DeferredSoundType;''')
s=replace(s,'    public static final DeferredBlock<AuraBlock> GREEN', '''    private static final DeferredRegister<SoundEvent> SOUNDS = DeferredRegister.create(Registries.SOUND_EVENT, MOD_ID);
    private static final DeferredHolder<SoundEvent, SoundEvent> RUSTLE_PLACE = SOUNDS.register("pouch.place",
        () -> SoundEvent.createVariableRangeEvent(ResourceLocation.fromNamespaceAndPath(MOD_ID, "pouch.place")));
    private static final DeferredHolder<SoundEvent, SoundEvent> RUSTLE_BREAK = SOUNDS.register("pouch.break",
        () -> SoundEvent.createVariableRangeEvent(ResourceLocation.fromNamespaceAndPath(MOD_ID, "pouch.break")));
    private static final DeferredHolder<SoundEvent, SoundEvent> RUSTLE_HIT = SOUNDS.register("pouch.hit",
        () -> SoundEvent.createVariableRangeEvent(ResourceLocation.fromNamespaceAndPath(MOD_ID, "pouch.hit")));
    private static final SoundType POUCH_SOUND = new DeferredSoundType(0.8F, 1.0F,
        RUSTLE_BREAK, () -> SoundEvents.WOOL_STEP, RUSTLE_PLACE, RUSTLE_HIT, () -> SoundEvents.WOOL_FALL);

    public static final DeferredBlock<AuraBlock> GREEN''')
s=replace(s,'BlockBehaviour.Properties.of().strength(0.25F).sound(SoundType.WOOD).noOcclusion()', '''BlockBehaviour.Properties.of().strength(0.2F, 0.2F).sound(POUCH_SOUND).noCollission().noOcclusion()
                        .ignitedByLava().pushReaction(PushReaction.DESTROY).lightLevel(state -> 8)''')
s=replace(s,'ITEMS.register(name, () -> new BlockItem(block.get(), new Item.Properties()));','''ITEMS.register(name, () -> new BlockItem(block.get(), new Item.Properties().stacksTo(64)) {
            @Override public Component getName(ItemStack stack) {
                int nameColor = switch (color) {
                    case "green" -> 0x55FF55;
                    case "yellow" -> 0xFFDD55;
                    case "red" -> 0xFF5555;
                    case "blue" -> 0x55AAFF;
                    case "purple" -> 0xBB77EE;
                    case "black" -> 0xAAAAAA;
                    default -> 0xFFFFFF;
                };
                return super.getName(stack).copy().withStyle(style -> style.withColor(nameColor));
            }
        });''')
s=replace(s,'        BLOCKS.register(bus);','        SOUNDS.register(bus);\n        BLOCKS.register(bus);')
write(p,s)
colors=['green','yellow','red','blue','purple','black']
for color in colors:
    p=assets/'blockstates'/f'{color}_guaiguai.json'
    old=json.loads(p.read_text())['variants']
    variants={}
    for k,v in old.items():
        for wet in ['false','true']:
            variants[k+',waterlogged='+wet]=v
    write(p,json.dumps({'variants':variants},indent=2)+'\n')
zh=['經典奶油椰子風味，香甜酥脆。','濃郁的五香風味，鹹香酥脆，令人忍不住一口接著一口。','香濃的巧克力風味，帶著恰到好處的甜味與酥脆口感。','清爽的海鹽風味，淡淡鹹香中帶著玉米的自然香氣。','香甜的葡萄風味，帶有濃郁果香與輕盈酥脆的口感。','濃厚的黑胡椒風味，鹹香中帶著微微辛辣的滋味。']
en=['Classic cream coconut flavor, sweet and crispy.','Rich five-spice flavor, savory and crispy, with every bite calling for another.','Rich chocolate flavor with just the right sweetness and a satisfying crunch.','Refreshing sea salt flavor with a light savory taste and natural corn aroma.','Sweet grape flavor with a rich fruity aroma and a light, crispy texture.','Bold black pepper flavor with a savory taste and a gentle spicy kick.']
for lang,descs,trad,subs in [('zh_tw',zh,'在某個小島上，似乎有著將它擺放在機器上，祈求設備不要損壞、乖乖運作的信仰。',['乖乖：包裝沙沙聲','乖乖：包裝碎裂聲','乖乖：包裝摩擦聲']),('en_us',en,'On a certain small island, there seems to be a belief in placing it on machines in the hope that they will not break down and will run properly.',['Guai Guai: Bag rustles','Guai Guai: Bag crinkles','Guai Guai: Bag crackles'])]:
    p=assets/'lang'/f'{lang}.json'
    d=json.loads(p.read_text())
    d.pop('tooltip.guaiguai.aura',None)
    for c,t in zip(colors,descs): d['tooltip.guaiguai.'+c]=t
    d['tooltip.guaiguai.green.tradition']=trad
    for k,t in zip(['place','break','hit'],subs): d['subtitles.guaiguai.pouch.'+k]=t
    write(p,json.dumps(d,ensure_ascii=False,indent=2)+'\n')
sounds={}
folder=assets/'sounds'/'pouch'
folder.mkdir(parents=True,exist_ok=True)
for kind,duration,amplitude,seed in [('place',.22,.34,710),('break',.30,.44,720),('hit',.13,.27,730)]:
    sounds['pouch.'+kind]={'subtitle':'subtitles.guaiguai.pouch.'+kind,'sounds':[f'guaiguai:pouch/{kind}_{i}' for i in range(1,4)]}
    for i in range(1,4):
        rng=random.Random(seed+i)
        rate=22050; n=int(rate*duration); prev=0; pcm=bytearray()
        bursts=[(rng.uniform(.005,duration*.78),rng.uniform(.004,.019),rng.uniform(.4,1)) for _ in range(6)]
        for j in range(n):
            t=j/rate
            w=rng.uniform(-1,1)
            high=(w-prev)*.5;prev=w
            env=math.sin(math.pi*t/duration)**1.2
            crack=sum(a*math.exp(-((t-c)/width)**2) for c,width,a in bursts)
            v=max(-1,min(1,amplitude*high*env*(.28+crack)))
            pcm+=struct.pack('<h',int(32767*v))
        with tempfile.TemporaryDirectory() as tmp:
            wav=pathlib.Path(tmp)/'sound.wav'
            with wave.open(str(wav),'wb') as out:
                out.setparams((1,2,rate,n,'NONE','not compressed'))
                out.writeframes(pcm)
            subprocess.run(['ffmpeg','-loglevel','error','-y','-i',str(wav),'-c:a','libvorbis','-q:a','3',str(folder/f'{kind}_{i}.ogg')],check=True)
write(assets/'sounds.json',json.dumps(sounds,indent=2)+'\n')
for name in ['build.gradle','src/main/resources/META-INF/neoforge.mods.toml']:
    p=root/name;write(p,p.read_text().replace('0.1.4','0.1.7'))
write(root/'tests'/'AuraTimingTest.java','''package tw.zonezero.guaiguai;
public final class AuraTimingTest {
    static void check(boolean b,String message){if(!b)throw new AssertionError(message);}
    public static void main(String[] args){
        check(AuraTiming.withinRadius(7,0,0,7),"boundary");
        check(!AuraTiming.withinRadius(7.001,0,0,7),"outside");
        check(!AuraTiming.withinRadius(5,5,0,7),"sphere");
        for(int d:new int[]{3600,6000}){
            check(AuraTiming.shouldRefresh(0,false,d-1200,d),"refresh");
            check(!AuraTiming.shouldRefresh(0,false,d-19,d),"duplicate");
            check(AuraTiming.shouldRefresh(0,false,d-20,d),"tolerance");
            check(!AuraTiming.shouldRefresh(1,false,1,d),"stronger");
            check(!AuraTiming.shouldRefresh(0,true,-1,d),"infinite");
            check(!AuraTiming.shouldRefresh(0,false,d+1,d),"longer");
        }
        int[] count=new int[1200];
        for(int x=0;x<1600;x+=16)for(int z=0;z<1600;z+=16){
            long pos=((long)x<<38)|((long)z<<12)|70;
            int t=AuraTiming.initialDelay(pos,1200);
            check(t>=1&&t<=1200,"delay range");
            count[t-1]++;
        }
        int used=0,peak=0;
        for(int c:count){if(c>0)used++;peak=Math.max(peak,c);}
        check(used>1150,"schedule spread");
        System.out.println("PASS: radius, refresh, spread; peak "+peak);
    }
}
''')
write(root/'tests'/'run-timing-tests.sh','''#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
javac -d "$tmp" src/main/java/tw/zonezero/guaiguai/AuraTiming.java tests/AuraTimingTest.java
java -cp "$tmp" tw.zonezero.guaiguai.AuraTimingTest
''')
p=root/'README_zh_TW.txt'
write(p,p.read_text()+'\n\nv0.1.7: 七格光環、光源8、含水、乾燥時可燃、無碰撞、支撐、活塞、名稱配色、商品介紹及最佳化；音效在建置時重新合成。\n')
print('v0.1.7 sources and resources generated.')
