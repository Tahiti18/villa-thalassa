import os

subpages = {
    'bedrooms': {
        'title': 'The Bedrooms',
        'subtitle': 'Four sun-drenched sanctuaries designed for deep rest and long-term comfort in Cyprus.',
        'hero_image': 'bedroom_1_1.jpg',
        'images': [
            'bedroom_1_1.jpg', 'bedroom_1_2.jpg', 
            'bedroom_2_1.jpg', 
            'bedroom_3_1.jpg', 
            'bedroom_4_1.jpg', 'bedroom_4_2.jpg',
            'bedroom_generic_1.jpg'
        ],
        'amenities': ['King, Queen & Twin beds available', 'Air Conditioning in all rooms', 'Blackout Curtains for deep sleep', 'Fresh Premium Linens', 'Ample Storage space', 'Toddler Bed Available upon request']
    },
    'kitchen': {
        'title': 'Kitchen & Dining',
        'subtitle': 'A gourmet kitchen and refined indoor dining area, perfect for preparing and enjoying local flavors.',
        'hero_image': 'kitchen_1.jpg',
        'images': ['kitchen_1.jpg', 'kitchen_2.jpg', 'dining_1.jpg', 'dining_2.jpg', 'dining_3.jpg', 'dining_4.jpg'],
        'amenities': [
            'Large Dining Table (Seats 8)', 'Modern Oven & Baking Setup', 'Dishwasher & Utilities', 
            'Coffee Station', 'Full Dinnerware Set', 'Open Plan Access to Outdoors', 
            'Blender & Toaster', 'BBQ Utensils'
        ]
    },
    'living-room': {
        'title': 'Living Area',
        'subtitle': 'A cozy, light-filled space for quiet evenings and Mediterranean afternoons.',
        'hero_image': 'living_room_1.jpg',
        'images': ['living_room_1.jpg', 'living_room_2.jpg'],
        'amenities': ['Smart TV with streaming apps', 'Comfortable Linen Seating', 'Air Conditioning', 'High-Speed Fiber WiFi']
    },
    'bathrooms': {
        'title': 'Bathrooms',
        'subtitle': 'Modern, refreshing spaces equipped with all the essentials.',
        'hero_image': 'bathroom_1.jpg',
        'images': ['bathroom_1.jpg', 'bathroom_2.jpg'],
        'amenities': ['Walk-in Showers', 'Fresh Towels provided', 'Hair Dryer', 'Premium Toiletries', 'Washing Machine']
    },
    'patio': {
        'title': 'Patio & Outdoors',
        'subtitle': 'Your private outdoor sanctuary for alfresco living under the Cyprus sun.',
        'hero_image': 'patio_table.jpg',
        'images': [
            'patio_table.jpg', 'patio_bar_1.jpg', 'patio_bar_2.jpg', 
            'patio_bbq.jpg', 'patio_pergola_1.jpg', 'patio_pergola_2.jpg'
        ],
        'amenities': ['Stone BBQ Station', 'Outdoor Bar & Seating', 'Sun Loungers', 'Dining Table & Pergola', 'Coastal Path Access']
    },
    'exterior': {
        'title': 'Exterior & Views',
        'subtitle': 'Admire the Mediterranean architecture and the stunning sea views of Paralimni.',
        'hero_image': 'exterior_house_1.jpg',
        'images': ['exterior_house_1.jpg', 'exterior_view_1.jpg', 'exterior_view_2.jpg', 'exterior_street.jpg'],
        'amenities': ['Private Property', 'Quiet Neighborhood', 'Sea Views', 'Mediterranean Architecture']
    },
    'driveway': {
        'title': 'Private Driveway',
        'subtitle': 'Secure and spacious parking within our gated property.',
        'hero_image': 'patio_driveway.jpg',
        'images': ['patio_driveway.jpg'],
        'amenities': ['Secure Parking', 'Space for Multiple Cars', 'Gated Entrance']
    }
}

template = """<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <meta name="description" content="Explore {{TITLE}} at Villa Thalassa, our boutique villa in Paralimni. {{SUBTITLE}}"/>
    <title>Villa Thalassa | {{TITLE}}</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=Manrope:wght@400;500;600&display=swap" rel="stylesheet"/>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css"/>
    <script id="tailwind-config">
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    colors: {
                        "nav-bg": "#232320", "on-surface": "#2d2a26", "surface": "#f4efe6", 
                        "primary": "#7a6b52", "secondary": "#2b566e", "primary-container": "#e8d8bd",
                        "primary-fixed-dim": "#d5c5a8"
                    },
                    fontFamily: { "headline": ["Playfair Display", "serif"], "body": ["Manrope"] }
                }
            }
        }
    </script>
    <style>
        .material-symbols-outlined { font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24; }
        .bg-glass { background: rgba(251, 249, 244, 0.7); backdrop-filter: blur(12px); }
        .ambient-shadow { box-shadow: 0px 20px 40px rgba(27, 28, 25, 0.06); }
        .luxury-pop { box-shadow: 0 40px 100px -20px rgba(0, 0, 0, 0.45); }
        .ghost-border { border: 1px solid rgba(207, 197, 185, 0.15); }
    </style>
</head>
<body class="bg-surface text-on-surface font-body selection:bg-primary-container pb-24">

<nav id="main-nav" class="fixed top-0 w-full z-50 bg-transparent transition-all duration-500 border-b border-white/0">
    <div class="flex justify-between items-center px-8 py-5 max-w-7xl mx-auto">
        <a href="villa_thalassa_local_lifestyle.html" class="flex items-center gap-2 text-white hover:text-primary-container transition-colors group">
            <span class="material-symbols-outlined group-hover:-translate-x-1 transition-transform">arrow_back</span>
            <span class="text-xl font-bold tracking-tighter font-headline">Back to Collection</span>
        </a>
        <div class="text-xl font-bold tracking-tighter text-white font-headline hidden md:block opacity-60">Villa Thalassa</div>
    </div>
</nav>

<main class="relative">
    <!-- Full Bleed Hero Section -->
    <section class="relative h-[80vh] flex items-center overflow-hidden w-full mb-32">
        <div class="absolute inset-0 z-0">
            <img class="w-full h-full object-cover" src="villaphotos/final/{{HERO_IMAGE}}" alt="{{TITLE}} Background">
            <div class="absolute inset-0 bg-gradient-to-t from-on-surface/80 via-on-surface/20 to-transparent"></div>
        </div>
        <div class="relative z-10 max-w-7xl mx-auto px-8 w-full">
            <div class="max-w-2xl text-white">
                <h1 class="font-headline text-5xl md:text-7xl font-extrabold tracking-tighter leading-tight mb-6">{{TITLE}}</h1>
                <p class="font-body text-xl opacity-90 leading-relaxed max-w-xl italic">{{SUBTITLE}}</p>
            </div>
        </div>
    </section>

    <!-- Gallery Section -->
    <section class="max-w-7xl mx-auto px-4 sm:px-8 mb-48">
        <div class="swiper mySwiper !py-20 !px-10 -mx-10 -my-20 overflow-visible">
            <div class="swiper-wrapper py-4">
                {{IMAGES_HTML}}
            </div>
        </div>
    </section>

    <!-- Amenities Section -->
    <section class="max-w-4xl mx-auto px-8 py-16 bg-white/50 backdrop-blur-sm border-[3px] border-primary-fixed-dim shadow-2xl">
        <h2 class="font-headline text-4xl font-bold mb-12 text-center text-primary tracking-tight underline decoration-primary-container underline-offset-8 decoration-4 uppercase">Included Amenities</h2>
        <ul class="grid grid-cols-1 md:grid-cols-2 gap-8 text-xl">
            {{AMENITIES_HTML}}
        </ul>
    </section>
</main>

<script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', function () {
        const swiper = new Swiper('.mySwiper', {
            slidesPerView: 'auto',
            spaceBetween: 60,
            centeredSlides: true,
            rewind: true,
            autoplay: {
                delay: 4500,
                disableOnInteraction: false,
            }
        });

        // Navbar scroll effect
        const nav = document.getElementById('main-nav');
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                nav.classList.remove('bg-transparent', 'border-white/0');
                nav.classList.add('bg-nav-bg', 'shadow-lg', 'border-white/5');
            } else {
                nav.classList.add('bg-transparent', 'border-white/0');
                nav.classList.remove('bg-nav-bg', 'shadow-lg', 'border-white/5');
            }
        });
    });
</script>
</body>
</html>
"""

def build_pages():
    for page, info in subpages.items():
        images_html = ""
        for img in info['images']:
            img_path = f"villaphotos/final/{img}"
            images_html += f'<div class="swiper-slide !w-auto flex justify-center items-center"><img src="{img_path}" class="h-[320px] md:h-[580px] w-auto max-w-[90vw] rounded-none border-[3px] border-primary-fixed-dim luxury-pop" alt="Villa Thalassa {page} photo"></div>\\n'
        
        amenities_html = ""
        for am in info['amenities']:
            amenities_html += f'<li class="flex items-center gap-4 font-semibold text-on-surface/90"><span class="material-symbols-outlined text-primary text-2xl font-bold">check_circle</span>{am}</li>\\n'
            
        final_html = template.replace('{{TITLE}}', info['title']).replace('{{SUBTITLE}}', info['subtitle']).replace('{{HERO_IMAGE}}', info['hero_image']).replace('{{IMAGES_HTML}}', images_html).replace('{{AMENITIES_HTML}}', amenities_html)
        
        target_path = f"C:/Users/mar1/Documents/testing/{page}.html"
        with open(target_path, "w", encoding='utf-8') as f:
            f.write(final_html)
        print(f"Generated {page}.html")

if __name__ == "__main__":
    build_pages()
