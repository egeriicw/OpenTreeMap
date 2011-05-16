from django import forms
from models import Tree, Species, TreePhoto, TreeStatus, TreeAlert, TreeAction, Neighborhood, ZipCode, ImportEvent, Choices, status_choices
from django.contrib.auth.models import User
from django.contrib.localflavor.us.forms import USZipCodeField
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from datetime import datetime

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, 
           help_text="Full Name", widget=forms.TextInput(attrs={'size':'40'}),required=False)
    subject = forms.CharField(max_length=100, 
              help_text="Subject of your message", widget=forms.TextInput(attrs={'size':'40'}))
    sender = forms.EmailField(
              help_text="Your email address", widget=forms.TextInput(attrs={'size':'40'}),required=True)
    message = forms.CharField(
              help_text="Please enter as much text as you would like", 
              widget=forms.Textarea(attrs={'rows':'12','cols':'60'}))
    cc_myself = forms.BooleanField(required=False, 
                help_text="Send yourself a copy of this message")
                
class TreeEditPhotoForm(forms.ModelForm):
    class Meta:
        model = TreePhoto
        exclude = ('reported_by',)
        fields = ('title','photo',)

class TreeAddForm(forms.Form):
    edit_address_street = forms.CharField(max_length=200, required=True, initial="Enter an Address or Intersection")
    edit_address_city = forms.CharField(max_length=200, required=False, initial="Enter a City")
    edit_address_zip = USZipCodeField(widget=forms.HiddenInput, required=False)
    lat = forms.FloatField(widget=forms.HiddenInput,required=True)
    lon = forms.FloatField(widget=forms.HiddenInput,required=True)
    species_name = forms.CharField(required=False, initial="Enter a Species Name")
    species_id = forms.CharField(widget=forms.HiddenInput, required=False)
    dbh = forms.FloatField(required=False)
    height = forms.FloatField(required=False)
    canopy_height = forms.IntegerField(required=False)
    plot_width = forms.IntegerField(required=False)
    plot_length = forms.IntegerField(required=False)
    plot_type = forms.TypedChoiceField(choices=Choices().get_field_choices('plot'), required=False)
    power_lines = forms.BooleanField(required=False, label='Power lines overhead')
    sidewalk_damage = forms.ChoiceField(choices=Choices().get_field_choices('sidewalk_damage'), required=False)
    condition = forms.ChoiceField(choices=Choices().get_field_choices('condition'), required=False)
    canopy_condition = forms.ChoiceField(choices=Choices().get_field_choices('canopy_condition'), required=False)
    action = forms.ChoiceField(choices=Choices().get_field_choices('action'),required=False)
    alert = forms.ChoiceField(choices=Choices().get_field_choices('alert'), required=False)
    target = forms.ChoiceField(choices=[('addsame', 'I want to add another tree using the same tree details'), ('add', 'I want to add another tree with new details'), ('edit', 'I\'m done! I want to receive confirmation')], initial='edit', widget=forms.RadioSelect)        

    def __init__(self, *args, **kwargs):
        super(TreeAddForm, self).__init__(*args, **kwargs)
        if not self.fields['plot_type'].choices[0][0] == '':        
            self.fields['plot_type'].choices.insert(0, ('','Select One...' ) )
            self.fields['power_lines'].choices.insert(0, ('','Select One...' ) )
            self.fields['sidewalk_damage'].choices.insert(0, ('','Select One...' ) )
            self.fields['condition'].choices.insert(0, ('','Select One...' ) )
            self.fields['canopy_condition'].choices.insert(0, ('','Select One...' ) )
            self.fields['action'].choices.insert(0, ('','Select One...' ) )
            self.fields['alert'].choices.insert(0, ('','Select One...' ) )


    def clean(self):        
        cleaned_data = self.cleaned_data  
        try:
            point = Point(cleaned_data.get('lon'),cleaned_data.get('lat'),srid=4326)  
            #nearby = Tree.objects.filter(geometry__distance_lte=(point, D(ft=10)))
            nbhood = Neighborhood.objects.filter(geometry__contains=point)
        except:
            raise forms.ValidationError("This tree is missing a location. Click the map to add a location for this tree.") 
        
        #if nearby.count() > 0:
        #    raise forms.ValidationError("The selected location is too close to an existing tree. Please check that the tree you are trying to enter is not already in the system or specify a different location.")
        
        if nbhood.count() < 1:
            raise forms.ValidationError("The selected location is outside our area. Please specify a different location.")
        
        return cleaned_data 
        
    def save(self,request):
        from django.contrib.gis.geos import Point
        species = self.cleaned_data.get('species_id')
        if species:
            spp = Species.objects.filter(symbol=species)
            if spp:
                new_tree = Tree(species=spp[0])
            else:
                new_tree = Tree()
        else:
            new_tree = Tree()
        address = self.cleaned_data.get('edit_address_street')
        if address:
            new_tree.address_street = address
            new_tree.geocoded_address = address
        city = self.cleaned_data.get('edit_address_city')
        if city:
            new_tree.address_city = city
        zip_ = self.cleaned_data.get('edit_address_zip')
        if zip_:
            new_tree.address_zip = zip_
        
        plot_width = self.cleaned_data.get('plot_width')
        if plot_width:
            new_tree.plot_width = plot_width
        plot_length = self.cleaned_data.get('plot_length')
        if plot_length:
            new_tree.plot_length = plot_length
        plot_type = self.cleaned_data.get('plot_type')
        if plot_type:
            new_tree.plot_type = plot_type
        power_lines = self.cleaned_data.get('power_lines')
        print power_lines
        if power_lines != "":
            print "saving pl %s" % power_lines
            new_tree.powerline_conflict_potential = power_lines

        import_event, created = ImportEvent.objects.get_or_create(file_name='site_add',)
        new_tree.import_event = import_event
        
        #import pdb;pdb.set_trace()
        pnt = Point(self.cleaned_data.get('lon'),self.cleaned_data.get('lat'),srid=4326)
        new_tree.geometry = pnt
        new_tree.last_updated_by = request.user
        new_tree.save()
        height = self.cleaned_data.get('height')
        if height:
            ts = TreeStatus(                
                reported_by = request.user,
                value = height,
                key = 'height',
                tree = new_tree)
            ts.save()
        canopy_height = self.cleaned_data.get('canopy_height')
        if canopy_height:
            ts = TreeStatus(                
                reported_by = request.user,
                value = canopy_height,
                key = 'canopy_height',
                tree = new_tree)
            ts.save()
        dbh = self.cleaned_data.get('dbh')
        if dbh:
            ts = TreeStatus(
                reported_by = request.user,
                value = dbh,
                key = 'dbh',
                tree = new_tree)
            ts.save()
        sidewalk_damage = self.cleaned_data.get('sidewalk_damage')
        if sidewalk_damage:
            ts = TreeStatus(
                reported_by = request.user,
                value = sidewalk_damage,
                key = 'sidewalk_damage',
                tree = new_tree)
            ts.save()
        condition = self.cleaned_data.get('condition')
        if condition:
            ts = TreeStatus(
                reported_by = request.user,
                value = condition,
                key = 'condition',
                tree = new_tree)
            ts.save()
        canopy_condition = self.cleaned_data.get('canopy_condition')
        if canopy_condition:
            ts = TreeStatus(
                reported_by = request.user,
                value = canopy_condition,
                key = 'canopy_condition',
                tree = new_tree)
            ts.save()
        alert = self.cleaned_data.get('alert')
        if alert:
            ts = TreeAlert(
                reported_by = request.user,
                value = datetime.now(),
                key = alert,
                solved = False,
                tree = new_tree)
            ts.save()
        action = self.cleaned_data.get('action')
        if action:
            ts = TreeAction(
                reported_by = request.user,
                value = datetime.now(),
                key = action,
                tree = new_tree)
            ts.save()
        
        return new_tree
       
class _TreeAddForm(forms.ModelForm):
    data_owner = forms.CharField(widget=forms.HiddenInput, required=False)
    geometry = forms.CharField(required=True)
    species = forms.CharField(required=True)
    #species = forms.CharField(required=False)

    def clean_data_owner(self):
        """
        generally should be the editing user, but if owner already exists, then keep it as it was
        """
        data = self.cleaned_data['data_owner']
        if data:
            user = User.objects.get(id=data)
            return user
        
    def clean_geometry(self):
        print self.cleaned_data['geometry']
        print self.validate_proximity(False, 0)
        if self.validate_proximity(False, 0) > 0:
            raise forms.ValidationError("Too close to another tree.")
    
        return self.geometry
    
    def clean_species(self):
        """
        for a new tree, we're expecting something in the form of: 
            "Accepted_Symbol,cultivar_name"
        where cultivar may be blank
        """
        data = self.cleaned_data['species']
        #if not data:
        #    return
        if data.isdigit():
            existing_species = Species.objects.get(id=int(data)) 
            if existing_species == self.instance.species:
                print 'species unchanged'
                return existing_species
        
        
        species,cultivar = data.split(',')
        result = Species.objects.filter(accepted_symbol=species)
        
        if cultivar:
            result = result.filter(cultivar_name = cultivar)
        if not result:
            raise forms.ValidationError("%s is an invalid species" % data)
        return result[0]

    class Meta:
        model = Tree
        fields = (
        'data_owner',
        'address_street',
        'address_city',
        'address_zip',
        'geometry',
        # not required will add in edit_form...
        #'species',
        #'condition',
        #'tree_owner',
        #'plot_length',
        #'plot_width',
        #'plot_type',
        #'powerline_conflict_potential',
        )

    def __init__(self, *args, **kwargs):
        super(TreeAddForm, self).__init__(*args, **kwargs)
