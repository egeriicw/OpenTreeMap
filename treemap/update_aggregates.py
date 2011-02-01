#!/usr/bin/env python

import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.dirname(here))

#from django.core.management import setup_environ
#mport settings
#setup_environ(settings)
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from profiles.models import *
from treemap.models import TreePhoto


from django.db import connection, transaction
from django.db.models import Count, Sum
from profiles.models import *
from treemap import models 
import datetime


def update_aggregates(base_model, ag_model, tree_geom):
    """
    Updates the aggregate tables.  TODO:  don't just overwrite old summaries
    example: update_aggregates(Neighborhood, AggregateNeighborhood)
    """
    gext = tree_geom.envelope
    ns = base_model.objects.all()#.filter(geometry__intersects=gext)
    for n in ns:
        print n
        agg =  ag_model.objects.filter(location=n)
        if agg:
            agg = agg[0]
        else:
            agg = ag_model(location=n)
        summaries = []
        trees = models.Tree.objects.filter(geometry__within=n.geometry)
        agg.total_trees = len(trees)
        agg.distinct_species = len(trees.values("species").annotate(Count("id")).order_by("species"))
        #TODO figure out how to summarize diff stratum stuff
        field_names = [x.name for x in models.ResourceSummaryModel._meta.fields 
            if not x.name == 'id']
        for f in field_names:
            fn = 'treeresource__' + f
            s = trees.aggregate(Sum(fn))[fn + '__sum'] or 0.0
            print agg,f,s
            setattr(agg,f,s)
        agg.save()
 
def cache_search_aggs(query_pairs=({'trees':models.Tree.objects.all(),'query':''},),return_first=False):
    #fields = ['annual_stormwater_management', 'annual_electricity_conserved', 
    #          'annual_natural_gas_conserved', 'annual_air_quality_improvement', 
    #          'annual_co2_sequestered', 'total_co2_stored', 
    #          'annual_co2_avoided'
    #          ]
              #'total_trees', 'distinct_species'
    for q in query_pairs:
        agg = models.AggregateSearchResult.objects.filter(key=q['query'])
        if agg:
            agg = agg[0]
        else:
            agg = models.AggregateSearchResult(key=q['query'])
        #if not new:
        #    agg.key = 
        trees = q['trees']
        # call len seems to cause deep crashing in python threads...
        #agg.total_trees = len(trees)
        #agg.distinct_species = len(trees.values("species").annotate(Count("id")).order_by("species"))
        agg.total_trees = trees.count()
        agg.distinct_species = trees.values("species").annotate(Count("id")).order_by("species").count()

        #TODO figure out how to summarize diff stratum stuff
        fields = [x.name for x in models.ResourceSummaryModel._meta.fields 
            if not x.name in ['id','aggregatesummarymodel_ptr','key','resourcesummarymodel_ptr','last_updated']]
        for f in fields:
                fn = 'treeresource__' + f
                s = trees.aggregate(Sum(fn))[fn + '__sum'] or 0.0
                print agg,f,s
                setattr(agg,f,s)
        agg.save()
        print 'saving', agg
        if return_first:
            return agg

               
def update_all_aggregates(verbose=False):
    tree_geom = models.Tree.objects.all().collect()
    update_aggregates(models.Neighborhood, models.AggregateNeighborhood, tree_geom)
    update_aggregates(models.ZipCode, models.AggregateZipCode, tree_geom)
    #cache_search_aggs()


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        update_aggregates(sys.argv[1])
    else:
        update_all_aggregates()
